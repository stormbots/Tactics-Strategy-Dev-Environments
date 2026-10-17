/* Memory-only unit translation unit: no constructor, socket or real receive. */
#define W2N_LOCAL_CHECKS
#include "observer.c"
#include <assert.h>
#include <setjmp.h>
#include <stdio.h>

static jmp_buf aborted;
static unsigned calls,mode;
static int expected_errno;
static int expected_fd=41;
static struct msghdr *expected_msg;
static unsigned tests;
static FILE *corpus;
static unsigned char control[300],payload[16400];
static struct iovec one;
static struct msghdr message,expected_before;
static struct iovec expected_one;
static void local_abort(void) {longjmp(aborted,125);}
static void header(uint8_t *b,size_t off,uint64_t n,uint32_t type) {
    p64(b,off,n);p32(b,off+8,SOL_SOCKET);p32(b,off+12,type);
}
static ssize_t fake_receive(int fd,struct msghdr *m,int flags) {
    calls++;assert(fd==expected_fd && m==expected_msg && flags==MSG_CMSG_CLOEXEC);
    assert(errno==expected_errno);
    if(mode==20) return w2n_local_recvmsg(fd,m,flags); /* mock recursion -> longjmp, not exit */
    if(mode==21){errno=EINTR;return -1;}
    if(mode==22){m->msg_control=(void*)(uintptr_t)1;m->msg_iov=(void*)(uintptr_t)1;errno=EFAULT;return -1;}
    if(!m){errno=EFAULT;return -1;}
    assert(memcmp(m,&expected_before,sizeof(*m))==0);
    assert(memcmp(&one,&expected_one,sizeof(one))==0);
    /* Detect any observer pre-zeroing/mutation of caller buffers. */
    assert(control[0]==0xa5 && payload[0]==0xb6);
    zeros(control,52);header(control,0,28,SCM_CREDENTIALS);
    p32(control,16,101);p32(control,20,1000);p32(control,24,1000);
    control[28]=0xde;control[29]=0xad;control[30]=0xbe;control[31]=0xef;
    m->msg_controllen=28;m->msg_flags=MSG_CMSG_CLOEXEC;
    if(S.case_id==2) {
        header(control,32,20,SCM_RIGHTS);p32(control,48,77);
        m->msg_controllen=52;m->msg_flags|=MSG_CTRUNC;
    }
    bytes(payload,"fixed synthetic payload",23);
    switch(mode) {
    case 1:m->msg_controllen=300;break;
    case 2:m->msg_control=(void*)(uintptr_t)1;break;
    case 3:m->msg_iov=(void*)(uintptr_t)1;break;
    case 4:one.iov_base=(void*)(uintptr_t)1;break;
    case 5:one.iov_len=1;break;
    case 6:m->msg_iovlen=2;break;
    case 7:p64(control,32,UINT64_MAX);break;
    case 8:p32(control,44,999);break;
    case 9:p64(control,32,21);m->msg_controllen=53;break;
    case 10:p32(control,48,UINT32_MAX);break;
    case 11:header(control,32,28,SCM_CREDENTIALS);m->msg_controllen=60;break;
    case 12:header(control,32,28,SCM_RIGHTS);m->msg_controllen=60;break;
    case 13:m->msg_controllen=12;break;
    case 14:m->msg_controllen=32;break; /* credentials + final padding only */
    default:break;
    }
    if(mode!=16)errno=73;
    return mode==15?300:23;
}
static void reset(unsigned which) {
    zeros(&A,sizeof(A));zeros(&S,sizeof(S));calls=0;mode=0;expected_fd=41;
    S.cookie=COOKIE;S.errno_slot=&errno;S.next=fake_receive;S.pid=101;
    S.selected_fd=S.last_fd=S.last_unarmed_fd=-1;S.resolution=1;abi_block();
    /* Synthetic provider, never represented as a real loader attestation. */
    bytes(A.provider,"W2NPROV1",8);p32(A.provider,8,1);p32(A.provider,12,512);
    p32(A.provider,16,14);p32(A.provider,20,15);p32(A.provider,64,7);p32(A.provider,68,101);
    bytes(A.provider+80,"recvmsg",7);bytes(A.provider+128,"/synthetic/lib",14);
    uint8_t run[16]={1};errno=61;
    assert(w2n_v1_setup(run,16,which,1)==OK && errno==61);
}
static void prepare(void) {
    for(size_t k=0;k<sizeof(control);k++)control[k]=0xa5;
    for(size_t k=0;k<sizeof(payload);k++)payload[k]=0xb6;
    zeros(&message,sizeof(message));one.iov_base=payload;one.iov_len=16384;
    message.msg_iov=&one;message.msg_iovlen=1;message.msg_control=control;
    message.msg_controllen=S.case_id==2?52:256;expected_msg=&message;
}
static ssize_t invoke(void) {
    if(expected_msg)bytes(&expected_before,expected_msg,sizeof(expected_before));
    bytes(&expected_one,&one,sizeof(one));
    expected_errno=errno=61;return w2n_local_recvmsg(expected_fd,expected_msg,MSG_CMSG_CLOEXEC);
}
static void admit(unsigned which) {
    reset(which);prepare();assert(invoke()==23 && calls==1 && errno==73);
    assert(S.lifecycle==READY && S.entries==1 && S.exits==1);
    errno=61;assert(w2n_v1_arm(41,1)==OK && errno==61);
    prepare();
}
static void freeze_valid(void) {
    assert(invoke()==23 && calls==2 && errno==73);
    assert(S.lifecycle==CAPTURED && S.quality==3);
    uint8_t untouched[512];for(size_t k=0;k<512;k++)untouched[k]=0x99;
    assert(w2n_v1_read(1,0,512,untouched,512)==NOT_READY);
    for(size_t k=0;k<512;k++)assert(untouched[k]==0x99);
    assert(w2n_v1_freeze()==OK && S.quality==1 && S.issues==0);
    assert(g64(A.capture,240)==255 && g32(A.capture,208)==31);
}
#define CHECK(name,...) do {__VA_ARGS__;tests++;printf("ok %u - %s\n",tests,name);if(S.lifecycle==FROZEN)assert(fwrite(A.capture,1,1536,corpus)==1536);}while(0)
int main(int argc,char **argv) {
    assert(argc==2);
    char corpus_path[512];int n=snprintf(corpus_path,sizeof(corpus_path),"%s.corpus",argv[1]);
    assert(n>0 && (size_t)n<sizeof(corpus_path));corpus=fopen(corpus_path,"wb");assert(corpus);
    CHECK("measured ABI/profile and storage bounds", {
        reset(1);assert(g32(A.abi,16)==1 && sizeof(A)==3584 && sizeof(S)<=512);
        uint8_t b[256];errno=29;assert(w2n_v1_abi(b,256)==OK && errno==29);
        assert(g32(b,44)==56 && g32(b,156)==52 && g32(b,184)==1536);
    });
    CHECK("healthy forwarding returns exact result/errno and one call", {
        admit(1);freeze_valid();assert(g32(A.capture,228)==1);
        assert(g64(A.capture,96)==2 && g64(A.capture,104)==2 && g64(A.capture,112)==1);
        assert(g32(A.capture,136)==61 && g32(A.capture,140)==73);
    });
    CHECK("fixed 52 byte synthetic record, final unpadded rights", {
        admit(2);freeze_valid();assert(g32(A.capture,228)==2 && g32(A.capture,168)==52);
        assert(g32(A.capture,132)&MSG_CTRUNC);assert(g32(A.capture,560)==77);
        assert(A.capture[768+48]==1 && g32(A.capture,216)==48);
        FILE *f=fopen(argv[1],"wb");assert(f);assert(fwrite(A.capture,1,1536,f)==1536);assert(fclose(f)==0);
    });
    CHECK("padding redaction and original memory intact", {
        admit(2);freeze_valid();
        for(size_t k=28;k<32;k++)assert(A.capture[512+k]==0 && A.capture[768+k]==0);
        assert(control[28]==0xde && control[29]==0xad && g32(control,48)==77);
        for(size_t k=52;k<256;k++)assert(A.capture[512+k]==0 && A.capture[768+k]==0);
        for(size_t k=0;k<256;k++)assert(A.raw_control[k]==0 && A.raw_payload[k]==0);
    });
    CHECK("immutable repeated freeze and three exact idempotent reads", {
        admit(2);freeze_valid();uint8_t copy[1536],again[512];
        for(uint32_t off=0;off<1536;off+=512)assert(w2n_v1_read(1,off,512,copy+off,512)==OK);
        assert(w2n_v1_freeze()==OK);assert(w2n_v1_read(1,512,512,again,512)==OK);
        assert(memcmp(copy,A.capture,1536)==0 && memcmp(copy+512,again,512)==0 && calls==2);
    });
    CHECK("all control calls preserve errno", {
        admit(1);freeze_valid();uint8_t b[512];errno=37;
        assert(w2n_v1_abi(b,256)==OK && errno==37);
        assert(w2n_v1_status(b,256)==OK && errno==37);
        assert(w2n_v1_provider(b,512)==OK && errno==37);
        assert(w2n_v1_read(1,0,512,b,512)==OK && errno==37);
        assert(w2n_v1_freeze()==OK && errno==37);
        assert(w2n_v1_arm(-1,1)==BAD_ARGUMENT && errno==37);
    });
    CHECK("bad ranges/generation leave output unchanged and mark live misuse", {
        admit(2);freeze_valid();uint8_t b[512],frozen[1536];bytes(frozen,A.capture,1536);
        for(size_t k=0;k<512;k++)b[k]=0xcc;
        assert(w2n_v1_read(1,UINT32_MAX,512,b,512)==BAD_RANGE);
        assert(w2n_v1_read(2,0,512,b,512)==BAD_GENERATION);
        assert(w2n_v1_status(b,255)==BAD_RANGE);
        for(size_t k=0;k<512;k++)assert(b[k]==0xcc);
        assert(S.issues&I_API);assert(memcmp(frozen,A.capture,1536)==0);
    });
    CHECK("real errors forward once, preserve EINTR, never inspect undefined output", {
        for(unsigned which=21;which<=22;which++) {
            admit(2);mode=which;assert(invoke()==-1 && calls==2 && errno==(which==21?EINTR:EFAULT));
            assert(w2n_v1_freeze()==OK && S.quality==3);
            assert(g64(A.capture,240)==49 && g32(A.capture,208)==17 && g32(A.capture,212)==3);
            for(size_t k=512;k<1536;k++)assert(A.capture[k]==0);
        }
    });
    CHECK("returned control and payload oversize remain bounded and invalid", {
        for(unsigned which=1;which<=15;which+=14) {
            admit(2);mode=which;assert(invoke()==(which==15?300:23));
            assert(w2n_v1_freeze()==OK && S.quality==2);
            assert(S.issues&(which==1?I_CONTROL:I_PAYLOAD));
            assert(g32(A.capture,168)<=52 && g32(A.capture,172)<=256);
        }
    });
    CHECK("changed pointers/count/base/length never dereference replacements", {
        for(unsigned which=2;which<=6;which++) {
            admit(2);mode=which;assert(invoke()==23 && calls==2);
            assert(w2n_v1_freeze()==OK && S.quality==2 && (S.issues&I_POINTER));
            if(which==2)assert(g32(A.capture,168)==0);
            else assert(g32(A.capture,172)==0 && g64(A.capture,192)==0);
        }
    });
    CHECK("malformed/unknown/partial/negative/duplicate controls fail sanitization", {
        for(unsigned which=7;which<=13;which++) {
            admit(2);mode=which;assert(invoke()==23);assert(w2n_v1_freeze()==OK);
            assert(S.quality==2 && (S.issues&I_SANITIZE) && g32(A.capture,212)==2);
            assert(g32(A.capture,224)!=UINT32_MAX);
            size_t bad=g32(A.capture,224);
            for(size_t k=bad;k<256;k++)assert(A.capture[512+k]==0 && A.capture[768+k]==0);
        }
    });
    CHECK("final padding is masked without inventing another header", {
        admit(2);mode=14;assert(invoke()==23);assert(w2n_v1_freeze()==OK && S.quality==1);
        assert(g32(A.capture,228)==1 && g32(A.capture,216)==28);
    });
    CHECK("later receive invalidates live coverage, not immutable capture", {
        admit(2);freeze_valid();uint8_t frozen[1536];bytes(frozen,A.capture,1536);
        prepare();assert(invoke()==23 && calls==3);assert(S.issues&I_MULTI);
        assert(S.win_entries==2 && S.win_exits==2 && memcmp(frozen,A.capture,1536)==0);
    });
    CHECK("wrong FD retains its original argument and marks invalid", {
        admit(2);expected_fd=42;assert(invoke()==23 && calls==2);
        assert(w2n_v1_freeze()==OK && S.quality==2 && (S.issues&I_FD));
    });
    CHECK("invalid original shape forwards once without copy", {
        admit(2);expected_msg=NULL;assert(invoke()==-1 && calls==2);
        assert(w2n_v1_freeze()==OK && S.quality==2 && (S.issues&I_SHAPE));
    });
    CHECK("counter saturation is sticky, not wrapping", {
        reset(1);S.entries=UINT64_MAX-1;prepare();assert(invoke()==23);
        assert(S.entries==UINT64_MAX && (S.issues&I_OVERFLOW));prepare();assert(invoke()==23);
        assert(S.entries==UINT64_MAX);
    });
    CHECK("recursive observer abort branch mocked, no OS process termination", {
        admit(2);mode=20;int code=setjmp(aborted);
        if(!code) {invoke();assert(!"recursive call must not return");}
        else assert(code==125 && calls==2 && (S.issues&I_RECURSE));
    });
    CHECK("ownership corruption abort branch mocked", {
        admit(2);S.cookie=0;int code=setjmp(aborted);
        if(!code){invoke();assert(!"corruption must not return");}
        else assert(code==125 && calls==1 && (S.issues&I_OWNER));
    });
    CHECK("setup/arm misuse never silently resets", {
        reset(1);uint8_t id[16]={1};assert(w2n_v1_setup(id,16,1,1)==BAD_STATE);
        assert(S.issues&I_API);assert(w2n_v1_arm(41,0)==BAD_STATE);
        admit(1);assert(w2n_v1_arm(41,1)==BAD_STATE && S.generation==1);
    });
    CHECK("failed initialization remains visible through status only", {
        reset(1);S.lifecycle=FAILED;S.resolution=2;S.issues=I_INIT;uint8_t b[512];
        for(size_t k=0;k<512;k++)b[k]=0xdd;
        assert(w2n_v1_provider(b,512)==INIT_FAILED && b[0]==0xdd);
        assert(w2n_v1_status(b,256)==OK && g32(b,16)==FAILED && g64(b,24)==I_INIT);
    });
    CHECK("duplicate credentials rejected within a complete bounded buffer", {
        admit(1);mode=11;assert(invoke()==23);assert(w2n_v1_freeze()==OK);
        assert(S.quality==2 && (S.issues&I_SANITIZE) && !(S.issues&I_CONTROL));
    });
    CHECK("unsupported incoming capacities/counts never copy caller data", {
        admit(2);message.msg_controllen=257;assert(invoke()==23 && calls==2);
        assert(w2n_v1_freeze()==OK && (S.issues&I_SHAPE) && g32(A.capture,168)==0);
        admit(2);message.msg_iovlen=2;assert(invoke()==23 && calls==2);
        assert(w2n_v1_freeze()==OK && (S.issues&I_SHAPE) && g32(A.capture,172)==0);
    });
    CHECK("argument/range precedence before unsafe output dereference", {
        reset(1);errno=43;
        assert(w2n_v1_status(NULL,255)==BAD_ARGUMENT && errno==43);
        assert(w2n_v1_read(1,0,511,(void*)(uintptr_t)1,512)==BAD_RANGE && errno==43);
        assert(w2n_v1_provider((void*)(uintptr_t)1,511)==BAD_RANGE);
        assert(w2n_v1_setup((void*)(uintptr_t)1,15,1,1)==BAD_ARGUMENT);
    });
    CHECK("all-zero fixture ID cannot configure or reset the instance", {
        reset(1);S.lifecycle=UNCONFIGURED;zeros(S.run,16);uint8_t zero[16]={0};
        assert(w2n_v1_setup(zero,16,1,1)==BAD_ARGUMENT && S.lifecycle==UNCONFIGURED);
        assert(S.issues&I_API);
    });
    CHECK("live status serializes actual identity/counts with reserved zeros", {
        admit(2);freeze_valid();uint8_t b[256];assert(w2n_v1_status(b,256)==OK);
        assert(g32(b,16)==FROZEN && g32(b,64)==101 && g64(b,80)==2 && g64(b,128)==2);
        assert(g32(b,124)==1536 && b[48]==1 && g64(b,72)==1);
        for(size_t k=144;k<256;k++)assert(b[k]==0);
    });
    CHECK("successful target that leaves errno unchanged is preserved", {
        admit(2);mode=16;assert(invoke()==23 && calls==2 && errno==61);
        assert(w2n_v1_freeze()==OK && g32(A.capture,140)==61 && S.quality==1);
    });
    assert(fclose(corpus)==0);
    printf("local_mock_checks=%u; native_receives=0; descriptors_transferred=0\n",tests);
    return 0;
}
