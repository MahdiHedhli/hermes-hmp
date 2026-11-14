/* Model-only Mach ABI subset. Never installed or used by native qualification. */
#ifndef HMP_TEST_MACH_H
#define HMP_TEST_MACH_H
#include <stdint.h>
typedef uint32_t mach_port_t;
typedef int kern_return_t;
#define MACH_PORT_NULL 0
#define KERN_SUCCESS 0
#define MACH_PORT_RIGHT_RECEIVE 1
#define MACH_MSG_TYPE_MAKE_SEND 20
mach_port_t mach_task_self(void);
kern_return_t mach_port_allocate(mach_port_t, int, mach_port_t *);
kern_return_t mach_port_insert_right(mach_port_t, mach_port_t, mach_port_t, int);
kern_return_t mach_port_mod_refs(mach_port_t, mach_port_t, int, int);
kern_return_t mach_port_deallocate(mach_port_t, mach_port_t);
#endif

#ifndef HMP_TEST_MESSAGE_H
#define HMP_TEST_MESSAGE_H
#include <stddef.h>
typedef uint32_t mach_msg_size_t;
typedef uint32_t mach_msg_timeout_t;
typedef uint32_t mach_msg_option_t;
typedef int32_t mach_msg_id_t;
typedef struct { uint32_t val[8]; } audit_token_t;
typedef struct {
    uint32_t msgh_bits, msgh_size;
    mach_port_t msgh_remote_port, msgh_local_port, msgh_voucher_port;
    mach_msg_id_t msgh_id;
} mach_msg_header_t;
typedef struct {
    uint32_t msgh_trailer_type, msgh_trailer_size, msgh_seqno;
    uint32_t security[2];
    audit_token_t msgh_audit;
} mach_msg_audit_trailer_t;
#define MAX_TRAILER_SIZE 128
#define MACH_MSG_TYPE_PORT_SEND 17
#define MACH_MSG_TYPE_PORT_SEND_ONCE 18
#define MACH_MSGH_BITS(remote, local) ((remote) | ((local) << 8))
#define MACH_PORT_VALID(p) ((p) != 0 && (p) != UINT32_MAX)
#define MACH_RCV_MSG 2
#define MACH_RCV_TIMEOUT 0x100
#define MACH_MSG_TRAILER_FORMAT_0 0
#define MACH_RCV_TRAILER_AUDIT 3
#define MACH_RCV_TRAILER_TYPE(t) 0
#define MACH_RCV_TRAILER_ELEMENTS(e) 0
#define MACH_MSG_SUCCESS 0
#define MACH_RCV_TIMED_OUT 0x10004003
kern_return_t mach_msg(mach_msg_header_t *, mach_msg_option_t, mach_msg_size_t,
                      mach_msg_size_t, mach_port_t, mach_msg_timeout_t, mach_port_t);
#endif

#ifndef HMP_TEST_DEAD_RIGHT_H
#define HMP_TEST_DEAD_RIGHT_H
typedef uint32_t mach_port_type_t;
typedef uint32_t mach_port_urefs_t;
#define MACH_PORT_RIGHT_DEAD_NAME 4
#define MACH_PORT_TYPE_DEAD_NAME (1u << 20)
#define MACH_PORT_TYPE_SEND_ONCE (1u << 18)
kern_return_t mach_port_type(mach_port_t, mach_port_t, mach_port_type_t *);
kern_return_t mach_port_get_refs(mach_port_t, mach_port_t, int, mach_port_urefs_t *);
#endif
