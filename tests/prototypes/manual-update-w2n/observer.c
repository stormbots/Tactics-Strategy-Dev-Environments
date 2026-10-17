/* W2n test observer only. No native schedule driver or production authority. */
#define _GNU_SOURCE
#include "observer.h"
#include <dlfcn.h>
#include <errno.h>
#include <limits.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

enum { OK, NOT_READY, BAD_ARGUMENT, BAD_STATE, UNSUPPORTED, INIT_FAILED,
       BAD_RANGE, BAD_GENERATION };
enum { UNCONFIGURED, READY, ARMED, IN_CALL, CAPTURED, FROZEN, RESERVED, FAILED };
enum { I_INIT=1u, I_PROFILE=2u, I_API=4u, I_MULTI=8u, I_FD=16u,
       I_RECURSE=32u, I_SHAPE=64u, I_POINTER=128u, I_CONTROL=256u,
       I_PAYLOAD=512u, I_REAL=1024u, I_SANITIZE=2048u,
       I_OVERFLOW=4096u, I_OWNER=8192u };
struct arena {
    uint8_t capture[1536], raw_control[256], raw_payload[256];
    uint8_t abi[256], status[256], provider[512], scratch[512];
};
struct state {
    uint64_t cookie, issues, generation, phase, entries, exits, arm_base;
    uint64_t win_entries, win_exits, last_call;
    uint32_t lifecycle, resolution, case_id, pid, quality;
    int32_t selected_fd, last_fd, last_unarmed_fd;
    uint8_t run[16];
    int *errno_slot;
    ssize_t (*next)(int, struct msghdr *, int);
    unsigned busy;
};
static struct arena A;
static struct state S;
_Static_assert(sizeof(struct arena)==3584, "arena ABI budget");
_Static_assert(sizeof(struct state)<=512, "scalar budget");
#define COOKIE UINT64_C(0x57326e7631000001)
#define INLINE static inline __attribute__((always_inline))
/* Volatile byte loops prevent replacement with lazy external memcpy/memset. */
INLINE void bytes(void *dst, const void *src, size_t n) {
    volatile uint8_t *d=dst; const volatile uint8_t *s=src;
    for (size_t k=0;k<n;k++) d[k]=s[k];
}
INLINE void zeros(void *dst, size_t n) {
    volatile uint8_t *d=dst;
    for (size_t k=0;k<n;k++) d[k]=0;
}
INLINE void p32(uint8_t *b,size_t o,uint32_t v) {
    for (size_t k=0;k<4;k++) b[o+k]=(uint8_t)(v>>(k*8));
}
INLINE void p64(uint8_t *b,size_t o,uint64_t v) {
    for (size_t k=0;k<8;k++) b[o+k]=(uint8_t)(v>>(k*8));
}
INLINE uint32_t g32(const uint8_t *b,size_t o) {
    uint32_t v=0; for(size_t k=0;k<4;k++) v|=(uint32_t)b[o+k]<<(8*k); return v;
}
INLINE uint64_t g64(const uint8_t *b,size_t o) {
    uint64_t v=0; for(size_t k=0;k<8;k++) v|=(uint64_t)b[o+k]<<(8*k); return v;
}
INLINE void bump(uint64_t *v) {
    if (*v==UINT64_MAX) S.issues|=I_OVERFLOW;
    else { ++*v; if (*v==UINT64_MAX) S.issues|=I_OVERFLOW; }
}
INLINE int32_t finish(int32_t result,int saved) {
    if(result!=OK && result!=NOT_READY && result!=UNSUPPORTED && result!=INIT_FAILED) S.issues|=I_API;
    errno=saved; return result;
}
INLINE int prerequisite(void) {
    if(S.lifecycle==FAILED || !S.next || !S.errno_slot)
        return (S.issues&I_INIT)?INIT_FAILED:UNSUPPORTED;
    if(g32(A.abi,16)!=1 || S.resolution!=1) return UNSUPPORTED;
    return OK;
}

static void abi_block(void) {
    uint16_t endian=1;
    uint32_t values[]={
        CHAR_BIT,sizeof(void*),sizeof(size_t),sizeof(ssize_t),sizeof(int),sizeof(long),
        sizeof(struct msghdr),_Alignof(struct msghdr),offsetof(struct msghdr,msg_name),
        offsetof(struct msghdr,msg_namelen),offsetof(struct msghdr,msg_iov),
        offsetof(struct msghdr,msg_iovlen),offsetof(struct msghdr,msg_control),
        offsetof(struct msghdr,msg_controllen),offsetof(struct msghdr,msg_flags),
        sizeof(struct iovec),_Alignof(struct iovec),offsetof(struct iovec,iov_base),
        offsetof(struct iovec,iov_len),sizeof(struct cmsghdr),_Alignof(struct cmsghdr),
        offsetof(struct cmsghdr,cmsg_len),offsetof(struct cmsghdr,cmsg_level),
        offsetof(struct cmsghdr,cmsg_type),sizeof(struct ucred),offsetof(struct ucred,pid),
        offsetof(struct ucred,uid),offsetof(struct ucred,gid),CMSG_LEN(0),CMSG_SPACE(0),
        CMSG_LEN(12),CMSG_SPACE(12),CMSG_LEN(4),CMSG_SPACE(4),
        CMSG_SPACE(sizeof(struct ucred))+CMSG_LEN(sizeof(int)),256,16384,256,
        sizeof(pid_t),sizeof(uid_t),sizeof(gid_t),1536,512,
        *(uint8_t*)&endian==1?1u:0u,sizeof(socklen_t),_Alignof(struct ucred)
    };
    static const uint32_t expected[]={
        8,8,8,8,4,8,56,8,0,8,16,24,32,40,48,16,8,0,8,16,8,0,8,12,
        12,0,4,8,16,16,28,32,20,24,52,256,16384,256,4,4,4,1536,512,1,4,4
    };
    _Static_assert(sizeof(values)==sizeof(expected),"ABI measured field count");
    zeros(A.abi,256); bytes(A.abi,"W2NABIv1",8); p32(A.abi,8,1); p32(A.abi,12,256);
    unsigned supported=1;
#ifndef __x86_64__
    supported=0;
#endif
    for(size_t k=0;k<sizeof(values)/sizeof(values[0]);k++) {
        p32(A.abi,20+4*k,values[k]); if(values[k]!=expected[k]) supported=0;
    }
    p32(A.abi,16,supported);
    if(!supported) S.issues|=I_PROFILE;
}

#ifndef W2N_LOCAL_CHECKS
static int provider_block(void) {
    Dl_info target={0}, own={0}; struct stat a,b;
    if(!dladdr((void*)S.next,&target) || !dladdr((void*)w2n_v1_status,&own) ||
       !target.dli_fname || !target.dli_sname || !target.dli_fbase ||
       target.dli_fbase==own.dli_fbase) return 0;
    char *path=realpath(target.dli_fname,NULL);
    if(!path) return 0;
    size_t n=strlen(path), symbol=strlen(target.dli_sname);
    const char *base=strrchr(path,'/');
    int valid=n>0 && n<=384 && symbol>0 && symbol<=48 && base &&
        strcmp(base+1,"libc.so.6")==0 &&
        (strcmp(target.dli_sname,"recvmsg")==0 || strcmp(target.dli_sname,"__recvmsg")==0) &&
        stat(path,&a)==0 && own.dli_fname && stat(own.dli_fname,&b)==0;
    if(valid) {
        zeros(A.provider,512); bytes(A.provider,"W2NPROV1",8);
        p32(A.provider,8,1);p32(A.provider,12,512);p32(A.provider,16,(uint32_t)n);
        p32(A.provider,20,15);p64(A.provider,24,a.st_dev);p64(A.provider,32,a.st_ino);
        p64(A.provider,40,(uintptr_t)S.next-(uintptr_t)target.dli_fbase);
        p64(A.provider,48,b.st_dev);p64(A.provider,56,b.st_ino);
        p32(A.provider,64,(uint32_t)symbol);p32(A.provider,68,S.pid);
        bytes(A.provider+80,target.dli_sname,symbol);bytes(A.provider+128,path,n);
    }
    free(path);return valid;
}
__attribute__((constructor)) static void initialize(void) {
    int saved=errno;
    S.cookie=COOKIE; S.errno_slot=&errno; S.pid=(uint32_t)getpid();
    S.selected_fd=S.last_fd=S.last_unarmed_fd=-1;
    abi_block();
    void *symbol=dlsym(RTLD_NEXT,"recvmsg");
    _Static_assert(sizeof(symbol)==sizeof(S.next),"function pointer representation");
    bytes(&S.next,&symbol,sizeof(symbol));
    if(!S.next) {S.issues|=I_INIT; S.resolution=2;S.lifecycle=FAILED;}
    else if(g32(A.abi,16)!=1 || !provider_block()) {
        S.issues|=I_PROFILE;S.resolution=2;S.lifecycle=FAILED;
    } else S.resolution=1;
    errno=saved;
}
#endif

W2N_API int32_t w2n_v1_setup(const uint8_t *run,uint32_t n,uint32_t which,uint64_t phase) {
    int saved=errno;int rc;
    if(!run || n!=16 || (which!=1 && which!=2) || phase!=1) return finish(BAD_ARGUMENT,saved);
    if((rc=prerequisite())!=OK) return finish(rc,saved);
    if(S.lifecycle!=UNCONFIGURED || S.entries || S.exits || S.issues) return finish(BAD_STATE,saved);
    unsigned any=0;for(size_t k=0;k<16;k++) any|=run[k];
    if(!any) return finish(BAD_ARGUMENT,saved);
    bytes(S.run,run,16);S.case_id=which;S.phase=phase;S.lifecycle=READY;
    return finish(OK,saved);
}
W2N_API int32_t w2n_v1_abi(uint8_t *out,uint32_t n) {
    int saved=errno;
    if(!out) return finish(BAD_ARGUMENT,saved);
    if(n!=256) return finish(BAD_RANGE,saved);
    bytes(out,A.abi,256);return finish(OK,saved);
}
W2N_API int32_t w2n_v1_provider(uint8_t *out,uint32_t n) {
    int saved=errno,rc;
    if(!out) return finish(BAD_ARGUMENT,saved);
    if(n!=512) return finish(BAD_RANGE,saved);
    if((rc=prerequisite())!=OK) return finish(rc,saved);
    bytes(out,A.provider,512);return finish(OK,saved);
}
W2N_API int32_t w2n_v1_status(uint8_t *out,uint32_t n) {
    int saved=errno;
    if(!out) return finish(BAD_ARGUMENT,saved);
    if(n!=256) return finish(BAD_RANGE,saved);
    uint8_t *b=A.status; zeros(b,256); bytes(b,"W2NSTAT1",8);
    p32(b,8,1);p32(b,12,256);p32(b,16,S.lifecycle);p32(b,20,S.resolution);
    p64(b,24,S.issues);p32(b,32,S.case_id);p64(b,40,S.phase);bytes(b+48,S.run,16);
    p32(b,64,S.pid);p32(b,68,(uint32_t)S.selected_fd);p64(b,72,S.generation);
    p64(b,80,S.entries);p64(b,88,S.exits);p64(b,96,S.arm_base);
    p64(b,104,S.win_entries);p64(b,112,S.win_exits);p32(b,120,(uint32_t)S.last_fd);
    p32(b,124,S.lifecycle==FROZEN?1536:0);p64(b,128,S.last_call);p32(b,136,S.quality);
    bytes(out,b,256);return finish(OK,saved);
}
W2N_API int32_t w2n_v1_arm(int32_t fd,uint64_t expected) {
    int saved=errno,rc;
    if(fd<0) return finish(BAD_ARGUMENT,saved);
    if((rc=prerequisite())!=OK) return finish(rc,saved);
    if(S.lifecycle!=READY || S.issues || S.entries!=1 || S.exits!=1 || expected!=S.entries ||
       S.last_unarmed_fd!=fd) return finish(BAD_STATE,saved);
    S.selected_fd=fd;S.arm_base=S.entries;S.generation=1;S.lifecycle=ARMED;
    return finish(OK,saved);
}

#ifdef W2N_LOCAL_CHECKS
/* Test translation unit supplies a non-returning mock abort; never a public API. */
static void local_abort(void) __attribute__((noreturn));
#define ABORT_OBSERVER() local_abort()
#define WRAPPER w2n_local_recvmsg
#else
#define ABORT_OBSERVER() _exit(125)
#define WRAPPER recvmsg
#endif

W2N_API ssize_t WRAPPER(int fd,struct msghdr *m,int flags) {
    /* Cached errno address belongs to this single trusted startup thread only. */
    if(!S.errno_slot || !S.next || S.cookie!=COOKIE || S.lifecycle>FAILED || S.lifecycle==RESERVED) {
        S.issues|=I_OWNER;ABORT_OBSERVER();
    }
    int entry_errno=*S.errno_slot;
    if(S.busy) {S.issues|=I_RECURSE;ABORT_OBSERVER();}
    S.busy=1;bump(&S.entries);S.last_fd=fd;
    const uint64_t call=S.entries;
    const int first=S.lifecycle==ARMED;
    const int window=S.lifecycle>=ARMED && S.lifecycle<=FROZEN;
    if(window) bump(&S.win_entries);
    if(!first && window) S.issues|=I_MULTI;
    if(S.lifecycle==UNCONFIGURED || S.lifecycle==READY) S.last_unarmed_fd=fd;
    void *control=NULL,*base=NULL;struct iovec *iov=NULL;
    size_t cap=0,count=0,length=0;int shape=0;
    if(first) {
        S.lifecycle=IN_CALL;zeros(A.capture,1536);zeros(A.raw_control,256);zeros(A.raw_payload,256);
        if(fd!=S.selected_fd) S.issues|=I_FD;
        if(m) {
            control=m->msg_control;cap=m->msg_controllen;iov=m->msg_iov;count=m->msg_iovlen;
            if(iov && count==1) {base=iov[0].iov_base;length=iov[0].iov_len;}
            shape=control && cap<=256 && cap==(S.case_id==2?52u:256u) &&
                iov && count==1 && base && length==16384 && flags==MSG_CMSG_CLOEXEC;
        }
        if(!shape) S.issues|=I_SHAPE;
        bytes(A.capture,"W2NCAP01",8);p32(A.capture,8,1);p32(A.capture,12,1536);p32(A.capture,16,512);
        p32(A.capture,32,S.case_id);p64(A.capture,40,S.phase);bytes(A.capture+48,S.run,16);
        p32(A.capture,64,S.pid);p32(A.capture,68,(uint32_t)fd);p64(A.capture,72,S.generation);
        p64(A.capture,80,call);p64(A.capture,88,S.arm_base);p32(A.capture,128,(uint32_t)flags);
        p32(A.capture,136,(uint32_t)entry_errno);p64(A.capture,152,cap);
        p64(A.capture,176,count);p64(A.capture,184,length);p32(A.capture,208,17);
        p32(A.capture,224,UINT32_MAX);p32(A.capture,232,(uint32_t)S.last_unarmed_fd);p32(A.capture,236,1);
    }
    *S.errno_slot=entry_errno;
    ssize_t result=S.next(fd,m,flags); /* The only normal-path external call. */
    int exit_errno=*S.errno_slot;
    bump(&S.exits);S.last_call=call;if(window) bump(&S.win_exits);
    if(first) {
        uint64_t available=49;uint32_t equality=17;
        p32(A.capture,140,(uint32_t)exit_errno);p64(A.capture,144,(uint64_t)result);
        p64(A.capture,96,S.entries);p64(A.capture,104,S.exits);
        p64(A.capture,112,S.win_entries);p64(A.capture,120,S.win_exits);
        if(result<0) {S.issues|=I_REAL;if(result!=-1) S.issues|=I_SHAPE;}
        else if(m) {
            p32(A.capture,132,(uint32_t)m->msg_flags);p64(A.capture,160,m->msg_controllen);available|=6;
            int same_control=m->msg_control==control;
            int same_iov=m->msg_iov==iov;
            int same_base=shape && same_iov && m->msg_iovlen==1 && iov[0].iov_base==base;
            if(same_control) equality|=2;
            if(same_iov) equality|=4;
            if(same_base) equality|=8;
            int same_length=same_base && iov[0].iov_len==length;
            if(!same_control || !same_iov || !same_base || !same_length) S.issues|=I_POINTER;
            if(same_length) {
                p64(A.capture,192,m->msg_iovlen);p64(A.capture,200,iov[0].iov_len);available|=8;
            }
            if(m->msg_controllen>cap || m->msg_controllen>256) S.issues|=I_CONTROL;
            if((uint64_t)result>length || result>256) S.issues|=I_PAYLOAD;
            if(shape && same_control) {
                size_t n=m->msg_controllen;if(n>cap)n=cap;if(n>256)n=256;
                bytes(A.raw_control,control,n);p32(A.capture,168,(uint32_t)n);
                if(m->msg_controllen<=cap && m->msg_controllen<=256)available|=64;
            }
            if(shape && same_length) {
                size_t n=(size_t)result;if(n>length)n=length;if(n>256)n=256;
                bytes(A.raw_payload,base,n);p32(A.capture,172,(uint32_t)n);
                if((uint64_t)result<=length && result<=256)available|=128;
            }
        }
        p32(A.capture,208,equality);p64(A.capture,240,available);
        S.quality=(S.issues&~(uint64_t)I_REAL)?2:3;S.lifecycle=CAPTURED;
    }
    S.busy=0;*S.errno_slot=exit_errno;return result;
}

static void show(size_t offset,size_t n) {
    for(size_t k=0;k<n;k++) {A.capture[512+offset+k]=A.raw_control[offset+k];A.capture[768+offset+k]=1;}
}
static void sanitize(void) {
    size_t span=g32(A.capture,168),off=0;unsigned creds=0,rights=0,headers=0;
    uint32_t bad=UINT32_MAX;
    while(off<span) {
        if(span-off<16) {bad=(uint32_t)off;break;}
        uint64_t len=g64(A.raw_control,off);uint32_t level=g32(A.raw_control,off+8),kind=g32(A.raw_control,off+12);
        if(len<16 || len>span-off || headers==16 || level!=SOL_SOCKET) {bad=(uint32_t)off;break;}
        size_t n=(size_t)len-16;int valid=1;
        if(kind==SCM_CREDENTIALS) {if(n!=12 || creds++)valid=0;}
        else if(kind==SCM_RIGHTS) {
            if(!n || n%4 || n>8 || rights+n/4>2)valid=0;
            else for(size_t k=0;k<n;k+=4)if(g32(A.raw_control,off+16+k)>INT32_MAX)valid=0;
            if(valid)rights+=(unsigned)(n/4);
        } else valid=0;
        if(!valid){bad=(uint32_t)off;break;}
        /* Unverified/malformed headers and their entire tail remain private. */
        show(off,16);show(off+16,n);headers++;
        size_t end=off+(size_t)len;
        if(end==span) {off=end;break;}
        /* len<=256 proves this alignment expression cannot overflow. */
        size_t next=off+(((size_t)len+7u)&~(size_t)7u);
        if(next>=span) {off=span;break;} /* final padding, including a short tail */
        off=next;
    }
    if(bad!=UINT32_MAX){S.issues|=I_SANITIZE;p32(A.capture,224,bad);}
    p32(A.capture,228,headers);p32(A.capture,212,bad==UINT32_MAX?1:2);
    unsigned visible=0;for(size_t k=0;k<256;k++)visible+=A.capture[768+k];p32(A.capture,216,visible);
}
W2N_API int32_t w2n_v1_freeze(void) {
    int saved=errno,rc;
    if((rc=prerequisite())!=OK)return finish(rc,saved);
    if(S.lifecycle==FROZEN)return finish(OK,saved);
    if(S.lifecycle!=CAPTURED)return finish(NOT_READY,saved);
    if(g64(A.capture,144)>>63) p32(A.capture,212,3);
    else {
        sanitize();size_t n=g32(A.capture,172);bytes(A.capture+1024,A.raw_payload,n);
        for(size_t k=0;k<n;k++)A.capture[1280+k]=1;
        p32(A.capture,220,(uint32_t)n);
    }
    zeros(A.raw_control,256);zeros(A.raw_payload,256);
    uint64_t avail=g64(A.capture,240);
    S.quality=(S.issues&~(uint64_t)I_REAL)?2:((S.issues&I_REAL)||avail!=255?3:1);
    p32(A.capture,20,S.quality);p64(A.capture,24,S.issues);S.lifecycle=FROZEN;
    return finish(OK,saved);
}
W2N_API int32_t w2n_v1_read(uint64_t generation,uint32_t offset,uint32_t n,uint8_t *out,uint32_t capacity) {
    int saved=errno,rc;
    if(!out)return finish(BAD_ARGUMENT,saved);
    if(n!=512 || capacity!=512 || (offset!=0 && offset!=512 && offset!=1024))return finish(BAD_RANGE,saved);
    if((rc=prerequisite())!=OK)return finish(rc,saved);
    if(S.lifecycle!=FROZEN)return finish(NOT_READY,saved);
    if(generation!=1)return finish(BAD_GENERATION,saved);
    bytes(out,A.capture+offset,512);return finish(OK,saved);
}
