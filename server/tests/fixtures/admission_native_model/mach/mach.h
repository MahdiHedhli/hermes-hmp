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
