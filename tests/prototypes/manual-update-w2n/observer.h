#ifndef W2N_OBSERVER_H
#define W2N_OBSERVER_H
#include <stdint.h>
#include <sys/socket.h>
#define W2N_API __attribute__((visibility("default")))
W2N_API int32_t w2n_v1_setup(const uint8_t *, uint32_t, uint32_t, uint64_t);
W2N_API int32_t w2n_v1_abi(uint8_t *, uint32_t);
W2N_API int32_t w2n_v1_provider(uint8_t *, uint32_t);
W2N_API int32_t w2n_v1_status(uint8_t *, uint32_t);
W2N_API int32_t w2n_v1_arm(int32_t, uint64_t);
W2N_API int32_t w2n_v1_freeze(void);
W2N_API int32_t w2n_v1_read(uint64_t, uint32_t, uint32_t, uint8_t *, uint32_t);
#endif
