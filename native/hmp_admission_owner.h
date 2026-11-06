#ifndef HMP_ADMISSION_OWNER_H
#define HMP_ADMISSION_OWNER_H

#include <stdbool.h>
#include <stdint.h>

/* Darwin-only retained endpoint foundation. No operation/terminal authority.
 * The fixed native startup owner must retain the returned allocation BEFORE
 * initialize. All calls are serial on the allocating process/thread. Never
 * expose this object, a port name or observed identity as a Python permit.
 */
typedef struct hmp_admission_owner hmp_admission_owner;

typedef enum {
    HMP_ADMISSION_EMPTY = 0,
    HMP_ADMISSION_ENDPOINT = 1,
    HMP_ADMISSION_REFUSED = 2,
    HMP_ADMISSION_CLOSED = 3,
    HMP_ADMISSION_REQUEST_OBSERVED = 4
} hmp_admission_state;

hmp_admission_owner *hmp_admission_owner_allocate(void);
bool hmp_admission_owner_initialize(hmp_admission_owner *, uint64_t work_end_ns,
                                    uint64_t cleanup_end_ns);
hmp_admission_state hmp_admission_owner_state(hmp_admission_owner *);
/* One fixed request observation, never admission. Endpoint remains unexported.
 * Actual input is restricted to owned fixture reply destinations until startup
 * and right provenance exist. Received rights/buffer remain retained; close and
 * disposal refuse until a separately reviewed message-disposal owner is added.
 * Even send-once disposal can notify its destination. No reply is sent here.
 */
bool hmp_admission_owner_observe_request(hmp_admission_owner *);
/* Close never authorizes another effect after its original cleanup deadline.
 * Unknown/late release is retained, not retried or represented as clean closure.
 */
bool hmp_admission_owner_close(hmp_admission_owner *);
/* Only a known timely CLOSED owner may be freed. Unknown owners stay retained. */
bool hmp_admission_owner_dispose(hmp_admission_owner **);

#endif
