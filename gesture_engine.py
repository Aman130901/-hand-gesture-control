import numpy as np
import json
import os
import logging
import shutil
from config import Config

logger = logging.getLogger(__name__)

class GestureEngine:
    def __init__(self, gestures_file=None):
        self.gestures_file = gestures_file or Config.GESTURES_FILE
        self.gestures = self.load_gestures()
        # Threshold for matching a gesture
        self.match_threshold = 0.85

    def load_gestures(self):
        if os.path.exists(self.gestures_file):
            try:
                with open(self.gestures_file, 'r') as f:
                    data = json.load(f)
                    logger.info(f"Loaded {len(data)} gestures: {list(data.keys())}")
                    return data
            except Exception as e:
                logger.error(f"Failed to load gestures: {e}")
        else:
            logger.warning(f"Gestures file not found at {self.gestures_file}. Starting fresh.")
        return {}

    def save_gesture(self, name: str, landmarks):
        """
        Saves a gesture sample. Appends to the list of samples for 'name'.
        """
        try:
            normalized = self._normalize_landmarks(landmarks)
            
            # Ensure list structure
            if name not in self.gestures:
                self.gestures[name] = []
            
            # Append new sample (convert np array to list for JSON serialization)
            self.gestures[name].append(normalized.tolist() if isinstance(normalized, np.ndarray) else normalized)
            
            os.makedirs(os.path.dirname(self.gestures_file), exist_ok=True)
            with open(self.gestures_file, 'w') as f:
                json.dump(self.gestures, f, indent=4)
            
            logger.info(f"Gesture '{name}' sample saved. Total samples: {len(self.gestures[name])}")
            return True
        except Exception as e:
            logger.error(f"Failed to save gesture '{name}': {e}")
            return False
            
    def delete_sample(self, name: str, index: int):
        """
        Deletes a specific sample at the given index.
        """
        if name in self.gestures:
            try:
                samples = self.gestures[name]
                if 0 <= index < len(samples):
                    samples.pop(index)
                    
                    # If empty, keep the key? Or delete? 
                    # Let's keep the key so the gesture still "exists" even if empty, until explicitly deleted.
                    
                    with open(self.gestures_file, 'w') as f:
                        json.dump(self.gestures, f, indent=4)
                    return True
            except Exception as e:
                logger.error(f"Error deleting sample: {e}")
        return False



    def rename_gesture(self, old_name: str, new_name: str):
        """
        Renames a gesture from old_name to new_name.
        """
        if old_name not in self.gestures:
            return False
        
        if new_name in self.gestures:
            # Prevent overwrite of existing gesture
            return False
            
        try:
            # 1. Update Memory
            self.gestures[new_name] = self.gestures.pop(old_name)
            
            # 2. Update JSON File
            with open(self.gestures_file, 'w') as f:
                json.dump(self.gestures, f, indent=4)
                
            # 3. Rename Folder (if exists)
            old_dir = os.path.join("samples", old_name)
            new_dir = os.path.join("samples", new_name)
            
            if os.path.exists(old_dir):
                # Ensure parent exists (should exist) and new dir doesn't (we checked gesture name, but check dir too)
                if not os.path.exists(new_dir):
                    os.rename(old_dir, new_dir)
            
            logger.info(f"Renamed gesture '{old_name}' to '{new_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to rename gesture: {e}")
            # Attempt rollback in memory? 
            # For simplicity, we assume partial failure handling is manual for now, or rare.
            return False

    def delete_gesture(self, name: str):
        """
        Deletes a gesture and its samples used for training.
        """
        if name in self.gestures:
            try:
                del self.gestures[name]
                with open(self.gestures_file, 'w') as f:
                    json.dump(self.gestures, f, indent=4)
                
                # Cleanup samples
                sample_dir = os.path.join("samples", name)
                if os.path.exists(sample_dir):
                    shutil.rmtree(sample_dir)
                
                return True
            except Exception as e:
                logger.error(f"Failed to delete gesture {name}: {e}")
            except Exception as e:
                logger.error(f"Failed to delete gesture {name}: {e}")
        return False

    def get_training_stats(self):
        """
        Calculates training metrics:
        1. Model Type: Geometric Vector Classifier (KNN-1)
        2. Loss: Average Intra-Cluster Variance (lower is better)
        3. Accuracy: Leave-One-Out Cross-Validation (LOOCV)
        """
        stats = {
            "model_type": "Geometric Vector Classifier (KNN)",
            "total_samples": 0,
            "accuracy": 0.0,
            "loss": 0.0,
            "breakdown": {}
        }

        # Flatten all samples for efficient LOOCV
        all_samples = []
        labels = []
        
        # 1. Calc Variance (Loss) per Gesture
        total_variance = 0
        gesture_count = 0
        
        for name, samples in self.gestures.items():
            if not samples: continue
            
            # Convert to numpy for math
            # Handle potential inconsistent list nesting from JSON
            clean_samples = []
            for s in samples:
                 if isinstance(s, list):
                     clean_samples.append(np.array(s))
                 else:
                     clean_samples.append(np.array(s)) # Already array?

            if not clean_samples: continue

            # Stack 
            data_stack = np.stack(clean_samples)
            
            # Variance (Mean squared distance from centroid)
            centroid = np.mean(data_stack, axis=0)
            distances = np.linalg.norm(data_stack - centroid, axis=1)
            variance = np.mean(distances ** 2)
            
            total_variance += variance
            gesture_count += 1
            
            # Add to global list for Accuracy check
            for s in clean_samples:
                all_samples.append(s)
                labels.append(name)
                
            stats["breakdown"][name] = {
                "samples": len(samples),
                "variance": float(variance)
            }

        stats["total_samples"] = len(all_samples)
        stats["loss"] = float(total_variance / gesture_count) if gesture_count > 0 else 0.0

        # 2. Calc Accuracy (LOOCV)
        # For each sample, treat it as "test" and others as "train"
        # Find nearest neighbor in "others". If label matches, Correct.
        
        if len(all_samples) < 2:
            stats["accuracy"] = 0.0 if not all_samples else 1.0 # Trivial
            return stats

        correct = 0
        total = len(all_samples)
        
        # Optimize: Compute full distance matrix once? Or simple loop for clarity.
        # Simple loop is fine for < 1000 samples.
        for i in range(total):
            test_sample = all_samples[i]
            true_label = labels[i]
            
            best_dist = float('inf')
            predicted_label = None
            
            for j in range(total):
                if i == j: continue # Skip self
                
                dist = np.linalg.norm(test_sample - all_samples[j])
                if dist < best_dist:
                    best_dist = dist
                    predicted_label = labels[j]
            
            if predicted_label == true_label:
                correct += 1
                
        stats["accuracy"] = (correct / total) * 100.0 if total > 0 else 0.0
        
        return stats

    def find_gesture(self, landmarks):
        """
        Compares input against all samples.
        Returns name if match is found and is not ambiguous.
        """
        if not self.gestures:
            return None

        current_feat = self._normalize_landmarks(landmarks)
        
        # Track top 2 matches for ambiguity check
        best_match = None
        min_dist = float('inf')
        
        second_best_dist = float('inf')
        second_best_match = None

        for name, samples in self.gestures.items():
            # Normalize samples list format
            if not isinstance(samples, list) or (len(samples) > 0 and not isinstance(samples[0], list)):
                if len(samples) > 0 and isinstance(samples[0], (int, float)):
                     samples = [samples]
            
            # Find closest sample for THIS gesture
            local_min = float('inf')
            for sample in samples:
                dist = self._calculate_distance(current_feat, sample)
                if dist < local_min:
                    local_min = dist
            
            # Now compare local_min to global bests
            if local_min < min_dist:
                # Update runner-up
                second_best_dist = min_dist
                second_best_match = best_match
                
                # New best
                min_dist = local_min
                best_match = name
            elif local_min < second_best_dist:
                second_best_dist = local_min
                second_best_match = name

        if min_dist < self.match_threshold:
            # Ambiguity Check
            ambiguity_margin = 0.10 
            
            if second_best_match and (second_best_dist - min_dist) < ambiguity_margin:
                logger.debug(f"Ambiguous: {best_match}({min_dist:.2f}) vs {second_best_match}({second_best_dist:.2f})")
                return None
                
            logger.debug(f"Matched: {best_match} | Dist: {min_dist:.3f}")
            return best_match
            
        return None

    def _normalize_landmarks(self, landmarks):
        """
        Converts 21 landmarks into a feature vector of angles.
        """
        # Convert to numpy array (21, 3)
        coords = []
        for lm in landmarks:
            if hasattr(lm, 'x'):
                coords.append([lm.x, lm.y, lm.z])
            else:
                coords.append(lm) # Assuming dict or list
        coords = np.array(coords)

        # Edges for angle calculation
        connections = [
            (0,1), (1,2), (2,3), (3,4),       # Thumb
            (0,5), (5,6), (6,7), (7,8),       # Index
            (0,9), (9,10), (10,11), (11,12),  # Middle
            (0,13), (13,14), (14,15), (15,16),# Ring
            (0,17), (17,18), (18,19), (19,20) # Pinky
        ]
        
        vectors = []
        for start, end in connections:
            v = coords[end] - coords[start]
            norm = np.linalg.norm(v)
            if norm == 0:
                v_norm = v
            else:
                v_norm = v / norm
            vectors.append(v_norm)
        
        angles = []
        
        # 1. Intra-finger angles (Curl)
        finger_indices = [
            [0,1,2,3], [4,5,6,7], [8,9,10,11], [12,13,14,15], [16,17,18,19] 
        ]
        
        for f_vecs in finger_indices:
            for i in range(len(f_vecs)-1):
                v1 = vectors[f_vecs[i]]
                v2 = vectors[f_vecs[i+1]]
                dot = np.dot(v1, v2)
                dot = np.clip(dot, -1.0, 1.0)
                angle = np.arccos(dot)
                angles.append(angle)
                
        # 2. Inter-finger spread
        bases = [0, 4, 8, 12, 16]
        for i in range(len(bases)-1):
            v1 = vectors[bases[i]]
            v2 = vectors[bases[i+1]]
            dot = np.dot(v1, v2)
            dot = np.clip(dot, -1.0, 1.0)
            angle = np.arccos(dot)
            angles.append(angle)

        return np.array(angles)

    def _calculate_distance(self, gesture1, gesture2):
        g1 = np.array(gesture1)
        g2 = np.array(gesture2)
        return np.linalg.norm(g1 - g2)
