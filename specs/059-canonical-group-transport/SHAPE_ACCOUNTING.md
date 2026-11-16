# GT1 native serialization and attachment shape accounting

Status: pinned source/AST/arithmetic findings only. This is not a production
frame/decoder budget, native execution or authorization pass. Fourteen native
source pins are recorded in source-pins.json at4162ecf1.

| Surface | Exact inspected behavior | Remaining transport/authority requirement |
| --- | --- | --- |
| groups.log | Native replay limits500 events and compact UTF-8 page2MiB. RPC wrapping is separate. Events/cursor/latest_seq/has_more/authority omit members and room revision. | Support complete pages with envelope; actual decoder/copies; member/history snapshot fence. |
| groups.list | At most500 room rows, each with members JSON bounded128KiB and up to128 members. | Default room count alone is not a small byte bound. Review complete pagination and ordering/mutation behavior without unauthorized roster/existence exposure. |
| groups.state | room_state, room_context and service.status composed separately. Context purpose500 characters, notes4KiB. | Bound driver status and full composition; no one-transaction snapshot claim. |
| groups.attachment.download | read_viewer requires committed event/room/authority context, then returns the whole file as data_base64 plus metadata. Native single-file limit15,000,000 bytes. | At maximum,20,000,000 base64 characters BEFORE metadata/RPC envelope. Generic client default8MiB and provisional8MiB retained ledger budget do not cover this surface. |
| groups.attachment.upload | Full strict base64 decode,15,000,000 single-file bytes; native message allows8 attachments/25,000,000 aggregate bytes. | Preserve complete supported shape and original media custody/consent. No automatic message submission or provider action. |
| HostedRoomAttachmentStore.read_range | Recipient-member read with viewer=False, event binding and whole-file digest metadata. | NOT equivalent to the viewer download contract. Do not substitute it for a phone by inventing a member or dropping viewer authorization. |
| Canonical serialization | serialize_frame uses json.dumps ensure_ascii=False with default whitespace; serialization error emits a fallback error. | Compact log-page budget is not the final frame size. Treat error/Unicode/metadata/result-copy shapes explicitly. |

The exact base64 expansion is ceil(15,000,000/3)*4 =20,000,000 ASCII
characters. This arithmetic establishes that a universal8MiB frame/retention
budget is insufficient; it does not establish the complete decoder/native/Python
heap/RSS peak or a final safe replacement number.

Choose and independently review a complete method-aware frame/aggregate budget
including simultaneous native return, base64/UTF-8/decoded/HTTP copies, or a genuinely
equivalent authorized viewer streaming interface if one is available. Neither
silently reducing file support nor using a recipient read as a viewer bypass is
acceptable. The portable ledger has explicit constructor limits and no runtime
caller/default; changing production budgets requires actual shape qualification.
At most one large operation or separate reservations may be appropriate, but this
is not frozen in GT1 by this source census.

Group attachments do not resolve the separate complete Photos AND Files/PDF
Phone Send source/consent/publication contract. Native support, HMP integration,
installed source, actual transport and signed-device/release acceptance remain
separate. No native attachment was read, uploaded, sent or decoded by this audit.
