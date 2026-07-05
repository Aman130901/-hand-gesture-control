import os
import struct

def fix_xauthority():
    auth_path = os.environ.get('XAUTHORITY')
    if not auth_path:
        home = os.environ.get('HOME')
        if home:
            auth_path = os.path.join(home, '.Xauthority')
            
    if not auth_path or not os.path.exists(auth_path):
        print("[fix_xauth] No XAUTHORITY found or file does not exist.")
        return False
        
    try:
        raw = open(auth_path, 'rb').read()
    except Exception as e:
        print(f"[fix_xauth] Error reading {auth_path}: {e}")
        return False
        
    entries = []
    n = 0
    while n < len(raw):
        try:
            if n + 2 > len(raw):
                break
            family, = struct.unpack('>H', raw[n:n+2])
            n += 2
            
            if n + 2 > len(raw):
                break
            length, = struct.unpack('>H', raw[n:n+2])
            n += length + 2
            addr = raw[n - length : n]
            
            if n + 2 > len(raw):
                break
            length, = struct.unpack('>H', raw[n:n+2])
            n += length + 2
            num = raw[n - length : n]
            
            if n + 2 > len(raw):
                break
            length, = struct.unpack('>H', raw[n:n+2])
            n += length + 2
            name = raw[n - length : n]
            
            if n + 2 > len(raw):
                break
            length, = struct.unpack('>H', raw[n:n+2])
            n += length + 2
            data = raw[n - length : n]
            
            entries.append((family, addr, num, name, data))
        except Exception:
            break
            
    # Add display '0' and display '1' entries for empty ones
    new_entries = list(entries)
    for family, addr, num, name, data in entries:
        if num == b'':
            new_entries.append((family, addr, b'0', name, data))
            new_entries.append((family, addr, b'1', name, data))
            
    # Serialize back
    out_path = '/tmp/xauth_fixed'
    try:
        with open(out_path, 'wb') as f:
            for family, addr, num, name, data in new_entries:
                f.write(struct.pack('>H', family))
                f.write(struct.pack('>H', len(addr)))
                f.write(addr)
                f.write(struct.pack('>H', len(num)))
                f.write(num)
                f.write(struct.pack('>H', len(name)))
                f.write(name)
                f.write(struct.pack('>H', len(data)))
                f.write(data)
        print(f"[fix_xauth] Wrote fixed Xauthority to {out_path}")
        # Print confirmation
        return True
    except Exception as e:
        print(f"[fix_xauth] Error writing to {out_path}: {e}")
        return False

if __name__ == '__main__':
    fix_xauthority()
