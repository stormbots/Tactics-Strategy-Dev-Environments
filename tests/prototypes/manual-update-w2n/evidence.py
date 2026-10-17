"""Pure W2n ABI/framing helpers. No loader, socket, actor, or native schedule driver."""
import ctypes
import hashlib
import json
import re
import struct

SIZES = {'abi': 256, 'status': 256, 'provider': 512, 'capture': 1536}
MAGIC = {'abi': b'W2NABIv1', 'status': b'W2NSTAT1',
         'provider': b'W2NPROV1', 'capture': b'W2NCAP01'}
U64_MAX = (1 << 64) - 1
ISSUES = (1 << 14) - 1
KEYS = {'kind', 'version', 'run', 'case', 'sample', 'block',
        'generation', 'call', 'total', 'offset', 'n', 'hex'}
EXPECTED_ABI = (8,8,8,8,4,8,56,8,0,8,16,24,32,40,48,16,8,0,8,16,8,0,8,12,
                12,0,4,8,16,16,28,32,20,24,52,256,16384,256,4,4,4,1536,512,1,4,4)


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def integer(value, maximum, name):
    require(type(value) is int and 0 <= value <= maximum, 'invalid ' + name)
    return value


def bind_verified_handle(lib):
    """Caller must verify RTLD_NOLOAD/identity; this helper NEVER loads a library."""
    p = ctypes.POINTER(ctypes.c_uint8)
    u32, u64 = ctypes.c_uint32, ctypes.c_uint64
    declarations = {
        'setup': [p, u32, u32, u64], 'abi': [p, u32], 'provider': [p, u32],
        'status': [p, u32], 'arm': [ctypes.c_int32, u64], 'freeze': [],
        'read': [u64, u32, u32, p, u32],
    }
    for name, args in declarations.items():
        fn = getattr(lib, 'w2n_v1_' + name)
        fn.argtypes, fn.restype = args, ctypes.c_int32
    return lib


def setup_arguments(run, case, phase):
    require(type(run) is bytes and len(run) == 16 and any(run), 'invalid run ID')
    require(type(case) is int and case in (1, 2), 'invalid case')
    require(type(phase) is int and phase == 1, 'invalid phase')
    return (ctypes.c_uint8 * 16).from_buffer_copy(run), 16, case, phase


def arm_arguments(fd, entries):
    integer(fd, (1 << 31) - 1, 'FD')
    integer(entries, U64_MAX, 'entry count')
    return fd, entries


def read_arguments(generation, offset, length=512, capacity=512):
    integer(generation, U64_MAX, 'generation')
    require(type(offset) is int and offset in (0, 512, 1024), 'invalid chunk offset')
    require(type(length) is int and type(capacity) is int and length == capacity == 512,
            'invalid chunk length/capacity')
    return generation, offset, length, (ctypes.c_uint8 * 512)(), capacity


def u32(b, off): return struct.unpack_from('<I', b, off)[0]
def i32(b, off): return struct.unpack_from('<i', b, off)[0]
def u64(b, off): return struct.unpack_from('<Q', b, off)[0]
def i64(b, off): return struct.unpack_from('<q', b, off)[0]


def control_view(data, mask, span):
    """Independent offset/mask parser, no native CMSG traversal and no FD operations."""
    require(len(data) == len(mask) == 256 and 0 <= span <= 256, 'control bounds')
    require(all(x in (0, 1) for x in mask), 'non-binary control mask')
    require(all(v == 0 for v, visible in zip(data, mask) if not visible), 'hidden control data')
    require(not any(mask[span:]), 'control visibility beyond span')
    allowed, headers, off, creds, rights = set(), [], 0, 0, 0
    bad = None
    while off < span:
        if span - off < 16:
            bad = off
            break
        if not any(mask[off:span]):
            bad = off  # the producer withheld the entire unverified header/tail
            break
        require(all(mask[off:off+16]), 'masked native header')
        allowed.update(range(off, off+16))
        length, level, kind = struct.unpack_from('<Qii', data, off)
        require(16 <= length <= span-off and len(headers) < 16 and level == 1,
                'unverified native header exposed')
        n = length - 16
        known = (kind == 2 and n == 12 and creds == 0) or (
            kind == 1 and n > 0 and n % 4 == 0 and n <= 8 and rights + n//4 <= 2)
        require(known, 'unverified control header exposed')
        require(all(mask[off+16:off+length]), 'hidden verified control data')
        fields = struct.unpack_from('<' + ('iii' if kind == 2 else 'i' * (n//4)), data, off+16)
        if kind == 1:
            require(all(fd >= 0 for fd in fields), 'visible negative rights FD')
            rights += n//4
        else:
            creds += 1
        allowed.update(range(off+16, off+length))
        headers.append(dict(offset=off, length=length, level=level, type=kind, values=list(fields)))
        end = off + length
        if end == span:
            off = span
        else:
            off = min(span, off + ((length + 7)//8)*8)
    require(set(n for n, visible in enumerate(mask) if visible) == allowed,
            'control mask hides/invents verified bytes')
    return headers, bad


def decode(block, raw):
    require(block in SIZES and type(raw) is bytes and len(raw) == SIZES[block], 'block size/type')
    require(raw[:8] == MAGIC[block] and u32(raw, 8) == 1 and u32(raw, 12) == len(raw), 'block header')
    if block == 'abi':
        require(raw[204:] == bytes(52), 'ABI reserved bytes')
        profile = u32(raw, 16)
        require(profile in (0, 1), 'unknown ABI profile')
        values = tuple(u32(raw, off) for off in range(20, 204, 4))
        if profile == 1:
            require(values == EXPECTED_ABI, 'ABI profile claims unsupported measurements')
        return dict(profile=profile, measured=values)
    if block == 'provider':
        n, flags, symbol = u32(raw, 16), u32(raw, 20), u32(raw, 64)
        require(1 <= n <= 384 and 1 <= symbol <= 48 and flags == 15, 'provider bounds/flags')
        require(raw[72:80] == bytes(8) and not any(raw[80+symbol:128]) and not any(raw[128+n:]),
                'provider reserved/tail bytes')
        name, path = raw[80:80+symbol], raw[128:128+n]
        require(b'\0' not in name+path and path.startswith(b'/'), 'provider names/path')
        require(u32(raw, 68) > 0, 'provider PID')
        return dict(path=path.hex(), symbol=name.hex(), pid=u32(raw, 68),
                    provider_dev=u64(raw, 24), provider_ino=u64(raw, 32))
    if block == 'status':
        state, resolution, issue = u32(raw, 16), u32(raw, 20), u64(raw, 24)
        require(state in (0,1,2,3,4,5,7) and resolution in (0,1,2) and not issue & ~ISSUES, 'status enums/bits')
        require(not any(raw[36:40]+raw[140:]), 'status reserved bytes')
        require(u32(raw, 136) in (0,1,2,3) and u32(raw, 124) == (1536 if state == 5 else 0), 'status quality/size')
        require(u32(raw,64)>0 and i32(raw,68)>=-1 and i32(raw,120)>=-1, 'status process/FD')
        require(u64(raw,88)<=u64(raw,80) and u64(raw,112)<=u64(raw,104), 'status counter ordering')
        if state in (1,2,3,4,5):
            require(resolution==1, 'configured status has no resolved target')
        if state==7:
            require(resolution==2 and issue & 3, 'failed initialization status')
        if state in (0,1,7):
            require(i32(raw,68)==-1 and u64(raw,96)==u64(raw,104)==u64(raw,112)==0 and u32(raw,136)==0,
                    'unarmed status carries armed fields')
        else:
            require(i32(raw,68)>=0 and u64(raw,96)==1, 'armed status endpoint/baseline')
            require(u32(raw,136) in ((0,) if state in (2,3) else ((2,3) if state==4 else (1,2,3))),
                    'status lifecycle/quality')
        generation, case = u64(raw, 72), u32(raw, 32)
        if state in (0,7) and case == 0:
            require(raw[48:64] == bytes(16) and u64(raw, 40) == 0, 'unconfigured identity')
        else:
            require(case in (1,2) and any(raw[48:64]) and u64(raw, 40) == 1, 'status fixture identity')
        require(generation == (1 if state in (2,3,4,5) else 0), 'status generation')
        if state in (0,7):require(case==0, 'initialization state has fixture identity')
        return dict(state=state, issues=issue, generation=generation, call=u64(raw, 128),
                    run=raw[48:64].hex(), case=case, pid=u32(raw, 64),
                    entries=u64(raw, 80), exits=u64(raw, 88), resolution=resolution,
                    quality=u32(raw,136), selected_fd=i32(raw,68), last_fd=i32(raw,120),
                    arm_base=u64(raw,96), window_entries=u64(raw,104), window_exits=u64(raw,112))
    require(u32(raw, 16) == 512 and not any(raw[36:40]+raw[248:512]), 'capture reserved/header bytes')
    quality, issues, availability, equality = u32(raw, 20), u64(raw, 24), u64(raw, 240), u32(raw, 208)
    require(quality in (1,2,3) and not issues & ~ISSUES and not availability & ~255 and not equality & ~31,
            'capture enum/bits')
    require(u32(raw, 32) in (1,2) and u64(raw, 40) == 1 and any(raw[48:64]) and u64(raw, 72) == 1,
            'capture fixture identity')
    require(u32(raw, 64) > 0 and i32(raw, 68) >= 0 and u32(raw, 236) == 1, 'capture process/FD/profile')
    cs, ps, cv, pv = (u32(raw, off) for off in (168,172,216,220))
    require(cs <= 256 and ps <= 256, 'capture spans')
    control, cm = raw[512:768], raw[768:1024]
    payload, pm = raw[1024:1280], raw[1280:1536]
    require(all(x in (0,1) for x in cm+pm), 'capture masks')
    require(cv == sum(cm) and pv == sum(pm) and not any(pm[ps:]), 'visibility counts/spans')
    require(not any(v for v, visible in zip(payload,pm) if not visible), 'hidden payload data')
    require(all(pm[:ps]), 'missing observed payload prefix')
    require(u32(raw, 212) in (1,2,3) and u32(raw, 228) <= 16, 'sanitizer enum/count')
    for bit, offsets, reader in [(1,(132,),u32),(2,(160,),u64),(3,(192,200),u64),(4,(136,),u32),(5,(140,),u32),(0,(144,),u64)]:
        if not availability & (1 << bit):
            require(all(reader(raw, off) == 0 for off in offsets), 'unavailable scalar exposed')
    bad_offset = u32(raw, 224)
    require(bad_offset == (1 << 32)-1 or bad_offset <= cs, 'bad control offset')
    if i64(raw, 144) < 0:
        require(availability == 49 and equality == 17 and not any(raw[512:]) and cs == ps == cv == pv == 0,
                'error exposes undefined output')
        require(u32(raw, 212) == 3 and u32(raw, 228) == 0 and issues & (1 << 10) and quality != 1,
                'error capture mislabeled')
        headers = []
    else:
        headers, bad = control_view(control, cm, cs)
        require(len(headers) == u32(raw, 228), 'header count mismatch')
        require((bad is None and u32(raw, 212) == 1 and bad_offset == (1 << 32)-1) or
                (bad is not None and u32(raw, 212) == 2 and bad_offset == bad and issues & (1 << 11)),
                'sanitizer result mismatch')
    if quality == 1:
        require(not issues and availability == 255 and equality == 31 and u32(raw, 212) == 1, 'false Valid capture')
        require(i32(raw, 128) == (1 << 30) and u64(raw, 152) == (256 if u32(raw,32)==1 else 52),
                'changed input flags/capacity')
        require(u64(raw,176) == u64(raw,192) == 1 and u64(raw,184) == u64(raw,200) == 16384, 'changed iovec')
        require(0 <= i64(raw,144) == ps and u64(raw,160) == cs, 'incomplete valid snapshot')
        require((u64(raw,80),u64(raw,88),u64(raw,96),u64(raw,104),u64(raw,112),u64(raw,120)) == (2,1,2,2,1,1),
                'wrong single-call window')
    return dict(quality=quality, issues=issues, generation=1, call=u64(raw,80),
                run=raw[48:64].hex(), case=u32(raw,32), pid=u32(raw,64),
                result=i64(raw,144), control=headers, payload_sha256=hashlib.sha256(payload[:ps]).hexdigest())


def _decimal(value):
    require(type(value) is str and re.fullmatch(r'0|[1-9][0-9]{0,19}', value) is not None, 'decimal ID')
    require(int(value) <= U64_MAX, 'decimal ID overflow')
    return int(value)


def envelope(raw, block, run, case, sample):
    details = decode(block, raw)
    setup_arguments(run, case, 1)
    integer(sample, 63, 'sample')
    generation = details.get('generation', 0)
    call = details.get('call', 0)
    if block in ('status','capture') and details.get('case', 0):
        require(details['case'] == case and details['run'] == run.hex(), 'binary/envelope fixture mismatch')
    result = []
    for off in range(0,len(raw),512):
        chunk=raw[off:off+512]
        obj=dict(kind='w2n-block',version=1,run=run.hex(),case=case,sample=sample,block=block,
                 generation=str(generation),call=str(call),total=len(raw),offset=off,n=len(chunk),hex=chunk.hex())
        line=json.dumps(obj,separators=(',',':'))+'\n'
        require(len(line.encode()) <= 2048, 'control line limit')
        result.append(line)
    return result


def assemble(lines):
    require(type(lines) is list and 1 <= len(lines) <= 3, 'chunk count')
    parts, identity = {}, None
    for line in lines:
        require(type(line) is str and line.endswith('\n') and len(line.encode()) <= 2048, 'chunk line bound')
        def pairs(items):
            obj={}
            for key,value in items:
                require(key not in obj, 'duplicate JSON key');obj[key]=value
            return obj
        try: obj=json.loads(line,object_pairs_hook=pairs)
        except (json.JSONDecodeError, UnicodeError, RecursionError) as exc: raise ValueError('invalid evidence JSON') from exc
        require(type(obj) is dict and set(obj) == KEYS, 'chunk schema')
        require(obj['kind']=='w2n-block' and type(obj['version']) is int and obj['version']==1, 'chunk version')
        require(type(obj['run']) is str and re.fullmatch('[0-9a-f]{32}',obj['run']) is not None and any(bytes.fromhex(obj['run'])), 'chunk run')
        require(type(obj['case']) is int and obj['case'] in (1,2), 'chunk case')
        integer(obj['sample'],63,'sample')
        block=obj['block'];require(type(block) is str and block in SIZES, 'chunk block')
        generation,call=_decimal(obj['generation']),_decimal(obj['call'])
        for name in ('total','offset','n'):integer(obj[name],1536,name)
        require(obj['total']==SIZES[block] and obj['offset']%512==0 and obj['offset']<obj['total'] and
                obj['n']==min(512,obj['total']-obj['offset']), 'chunk range')
        require(type(obj['hex']) is str and re.fullmatch('[0-9a-f]{'+str(2*obj['n'])+'}',obj['hex']) is not None, 'chunk hex')
        key=(obj['run'],obj['case'],obj['sample'],block,generation,call,obj['total'])
        require(identity is None or key==identity, 'mixed chunk identity')
        identity=key;require(obj['offset'] not in parts, 'duplicate chunk range');parts[obj['offset']]=bytes.fromhex(obj['hex'])
    require(set(parts)==set(range(0,identity[-1],512)), 'missing chunk range')
    raw=b''.join(parts[off] for off in sorted(parts));details=decode(identity[3],raw)
    require(details.get('generation',0)==identity[4] and details.get('call',0)==identity[5], 'chunk/binary IDs')
    if identity[3] in ('status','capture') and details.get('case',0):
        require(details['run']==identity[0] and details['case']==identity[1], 'chunk/binary fixture')
    return raw


def require_observer_consistency(capture, status):
    """Observer integrity only, never an authentication/cleanup acceptance function."""
    c,s=decode('capture',capture),decode('status',status)
    require(c['quality']==1 and not c['issues'] and s['state']==5 and not s['issues'], 'observer not complete')
    require((c['run'],c['case'],c['pid'],c['generation'],c['call']) ==
            (s['run'],s['case'],s['pid'],s['generation'],s['call']), 'status/capture identity')
    require(s['entries']==s['exits']==2, 'post-freeze entry')
    require(s['quality']==c['quality']==1 and s['resolution']==1, 'final status capture quality/resolution')
    require(s['selected_fd']==s['last_fd']==i32(capture,68)==i32(capture,232), 'status/capture endpoint')
    require(s['arm_base']==u64(capture,88) and s['window_entries']==u64(capture,112) and
            s['window_exits']==u64(capture,120), 'status/capture window counts')
    return dict(observer_integrity='Consistent', authentication_safety='Unproven', production_readiness=False)


class BoundedReport:
    """In-memory bounded evidence; caller still owns secure file persistence/cleanup."""
    LIMIT=128*1024
    RESERVE=4096

    def __init__(self):
        self.records=[];self.size=0;self.stopped=False;self.terminal=None;self.overflow=False

    def append(self, record):
        require(not self.stopped, 'report already stopped')
        encoded=(json.dumps(record,separators=(',',':'),allow_nan=False)+'\n').encode()
        if self.size+len(encoded)>self.LIMIT-self.RESERVE:
            self.stopped=True;self.overflow=True
            return False
        self.records.append(encoded);self.size+=len(encoded)
        return True

    def finish(self, outcome):
        require(self.terminal is None or self.stopped, 'terminal already recorded')
        if self.terminal is None:
            final=(dict(observation_result='Incomplete',reason='report overflow',original_outcome=outcome)
                   if self.overflow else outcome)
            encoded=(json.dumps(final,separators=(',',':'),allow_nan=False)+'\n').encode()
            require(len(encoded)<=self.RESERVE, 'terminal reserve exceeded')
            self.terminal=encoded;self.stopped=True
        require(self.size+len(self.terminal)<=self.LIMIT, 'report bound')
        return b''.join(self.records)+self.terminal
