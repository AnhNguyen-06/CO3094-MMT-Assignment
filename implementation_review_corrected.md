# Đính chính: đối chiếu implementation StreapRous với Chapter 3

## Phạm vi và cách đọc

Tài liệu này kiểm tra nội dung trong `Pasted text.txt` với `Chapter_3_v8.0.md`, `CO3094_streaprous_study_guide.md` và source hiện có. Chapter 3 là nguồn ưu tiên cho khái niệm transport; study guide hỗ trợ định vị và phân công nhưng một số nhận định trạng thái source trong đó không còn khớp với code hiện tại. Đây là đánh giá bằng cách đọc mã, chưa chạy framework.

## Kết luận

Source có một phần Reliability đã được viết: chia dữ liệu theo `MSS=1300`, giữ các segment chưa ACK trong `unacked`, ước lượng RTT/RTO, retransmit khi timeout và fast retransmit khi có 3 duplicate ACK. Vì vậy, mô tả trong bản đính kèm rằng sender “chưa có timer/retransmission” và “đẩy cả payload thành một segment” là sai với source hiện tại.

Các phần còn thiếu hoặc chưa hoàn chỉnh gồm: xác thực checksum TCP ở đầu nhận; receiver buffer và xử lý out-of-order; sender sliding/congestion/receive window; congestion control; và quản lý connection/FIN đầy đủ. Đường gửi/đóng raw trong HTTP adapter hiện bị comment nên phần transport đã có trong helper chưa được tích hợp đầy đủ vào ứng dụng.

## Các nhận định cần sửa

| Nhận định trong bản đính kèm | Đối chiếu đúng với source và slide |
|---|---|
| `cwnd` bắt đầu bằng 1 MSS, `ssthresh` bằng 65536 byte như mặc định | Slide 123 nêu `cwnd=1 MSS` cho slow start. Slide 124 nói khi có loss thì đặt `ssthresh` bằng một nửa `cwnd` ngay trước loss; 64 KB xuất hiện trong sơ đồ ví dụ slide 125, không phải giá trị khởi tạo bắt buộc. Code hiện chưa có `cwnd`/`ssthresh`. |
| MSS trong dự án | Nhóm xác nhận **MTU=1500 B** và đính chính MSS mong muốn là **1460 B** (ghi nhầm MSS=1500 trước đó). Với IPv4/TCP header cơ bản 20 B mỗi loại, 1500 - 20 - 20 = 1460 B payload TCP. TCP options làm giảm payload tối đa tương ứng. Source đã được cập nhật `MSS=1460`. |
| Chưa có retransmission timer, `wait_for_ack()` cần viết mới | Source đã có `RttEstimator`, `wait_for_ack()`, RTO/backoff, Karn-style không lấy mẫu RTT từ segment retransmit, tối đa retry, và fast retransmit ở 3 duplicate ACK. Đây là phần triển khai có thật, nhưng cần kiểm tra logic và tích hợp; không nên kết luận đã đạt TCP reliability hoàn chỉnh. |
| `run_conn_send()` gửi mọi segment rồi mới chờ ACK | Đúng về luồng hiện tại: nó chia payload thành các segment rồi gửi hết trong vòng `for`, sau đó mới gọi `wait_for_ack()`. Nhưng không đúng khi nói payload chỉ là một segment. Đây chưa phải sender có cửa sổ trượt giới hạn lượng in-flight. |
| Sender buffer chưa có | Có dictionary cục bộ `unacked` lưu chunk, thời điểm gửi và trạng thái retransmit cho đến khi ACK. Đây là buffer retransmission tạm cho một lần gọi gửi, không phải send buffer đầy đủ, tồn tại xuyên suốt connection. |
| Receiver “return ngay khi nhận một packet” và không chạy receive loop | `run_conn_recv()` chạy vòng lặp, bỏ packet không phù hợp và chỉ return khi nhận payload in-order đầu tiên hoặc FIN/RST. Nó chưa phải vòng đọc byte stream liên tục; out-of-order bị dup-ACK rồi drop, không được buffer. |
| Mọi gói nhận hiện chưa có checksum verify | Hàm `verify_tcp_checksum()` đã tồn tại, nhưng trong luồng `accept()`, `run_conn_recv()` và `wait_for_ack()` chưa thấy gọi hàm này trước khi xử lý segment/ACK. Nên nói “helper có nhưng chưa được áp dụng ở các đường nhận đã rà”. |
| Bắt tay 3 bước hoàn toàn chưa có | `accept()` đã có xử lý SYN, SYN-ACK và ACK cuối. Đây là skeleton handshake, nhưng code phải được rà về xác thực ACK mong đợi, sequence/state, retransmission và các trường hợp mất/lặp. Slide 101 nêu nguyên tắc handshake, không buộc phải viết hàm `connect()` nếu phạm vi chỉ triển khai server. |
| `connect()` là bắt buộc cho P2P theo Chapter 3 | Chapter 3 trình bày TCP client gọi connect trong ví dụ API (slide 101), nhưng không quy định ứng dụng P2P hay bắt buộc phải bổ sung hàm raw `connect()` trong assignment. Study guide ghi đây là thiếu sót của API hiện tại; nên ghi là nhu cầu kiến trúc ứng dụng nếu mỗi peer phải chủ động mở kết nối, không gán thành yêu cầu riêng của slide. |
| Công thức `rwnd = RcvBuffer - (LastByteRcvd - LastByteRead)` là công thức slide | Slide 94–95 giải thích bằng sơ đồ: `rwnd` quảng bá vùng đệm còn trống; sender giới hạn dữ liệu in-flight theo rwnd. Công thức trên là cách biểu diễn suy ra, cần định nghĩa byte đầu/cuối và cách tính buffer để tránh lệch 1 hoặc tính trùng out-of-order. |
| Bắt buộc `BytesInFlight <= min(cwnd,rwnd)` | Đây là kết hợp hợp lý từ slide 94 (giới hạn theo `rwnd`) và 122 (giới hạn theo `cwnd`), nhưng không phải một câu trích nguyên văn slide. Ghi là quy tắc tích hợp suy ra; trong source hiện tại chưa có cả hai cửa sổ. |
| MSS/MTU và fragmentation | Nhóm xác nhận **MTU=1500 B**, MSS được đính chính là **1460 B**. Với IPv4/TCP header cơ bản, đây là payload TCP vừa packet 1500 B. Nếu TCP options hoặc IP options được dùng thì effective payload MSS phải giảm. `build_ip_header()` vẫn tạo `flags_fragment=0x4000` nhưng pack `flags_offset=0`, nên DF chưa thực sự được bật; đây là vấn đề còn lại riêng của IP header. |
| `close_connection()` cần được viết mới | Hàm đã có: gửi FIN rồi xóa connection và queue ngay. Đây là đóng rất sơ sài, chưa giữ state/đợi ACK và chưa triển khai đầy đủ FIN state machine như slide 103–104. Đồng thời lời gọi raw send/close trong `daemon/httpadapter.py` đang comment. |
| TODO route hook / parser có thể xếp vào Reliability | Đây là phần tích hợp HTTP/app, không phải bản thân cơ chế Reliability Chapter 3. Nêu riêng để phân công, không trộn với yêu cầu transport. |

## Trạng thái code theo nhóm khái niệm

### Reliability

- **Đã có một phần:** `checksum()` để tạo checksum gửi; `verify_tcp_checksum()` helper và hiện được gọi để loại packet checksum sai ở các đường nhận đã sửa; `MSS=1460`; sequence arithmetic modulo 32-bit; phân loại in-order/duplicate/gap; sender giữ các chunk chưa ACK; RTT estimator; timeout retransmission có exponential backoff; fast retransmit sau 3 duplicate ACK.
- **Còn thiếu/sai:** verify checksum chưa được gọi ở các đường nhận; receiver không buffer out-of-order mà bỏ gói và gửi ACK tại byte đang chờ; ACK/data được xử lý chưa đầy đủ và sender tiêu thụ ACK trong `wait_for_ack()` theo từng lần gửi; trạng thái buffer/timer chỉ cục bộ; retry thất bại trả lỗi nhưng chưa có phục hồi connection tổng thể.
- **Kết luận:** có cơ chế Reliability từng phần, không phải “chưa implement”, cũng chưa đủ để tuyên bố truyền byte stream tin cậy hoàn chỉnh.

### Flow control

- Header outbound đang hardcode `window=5840` ở cả `build_tcp_packet()` và `send_tcp_data_segment()`.
- Trường window nhận được unpack cùng TCP header nhưng không dùng làm `peer_rwnd`.
- Chưa thấy receive buffer theo byte gắn với ứng dụng đọc, quảng bá `rwnd` động, hoặc sender giới hạn in-flight theo `rwnd`.
- Kết luận: flow control động theo slide 90–95 chưa được triển khai. Giá trị 5840 tự nó không chứng minh có receive buffer/window thật.

### Congestion control

- Chưa thấy `cwnd`, `ssthresh`, slow start, congestion avoidance hay điều chỉnh theo ACK/loss trong state hoặc đường gửi.
- `wait_for_ack()` có retransmission khi loss, nhưng retransmission không đồng nghĩa congestion control.
- Kết luận: AIMD/congestion control chưa được triển khai. Nếu nhóm chọn AIMD, phải ghi rõ phần slow start/fast recovery nào theo các slide 120–125 và tránh gọi mọi cập nhật `cwnd` là một thuật toán hoàn chỉnh.

### Kết nối

- Có server-side `accept()` xử lý handshake ba bước; có `close_connection()` gửi FIN; nhận FIN/RST có xử lý cơ bản.
- Chưa có FSM đóng đầy đủ và các nhánh hiện xóa state sớm. API raw không có `connect()` chủ động.
- Kết luận: đã có khung handshake/close, chưa phải quản lý kết nối hoàn chỉnh. Đóng góp P2P cần được xác định từ yêu cầu ứng dụng, không suy ra chỉ từ slide transport.

## Đính chính nội dung đề xuất triển khai

1. Giữ và rà soát các phần sender reliability đã có (`run_conn_send`, `wait_for_ack`, `RttEstimator`) thay vì viết lại như chưa tồn tại. Bổ sung test/đo kiểm chỉ khi nhóm sẵn sàng; tài liệu này chưa chạy code.
2. Ưu tiên sửa receiver: kiểm checksum trước khi xử lý; dùng cumulative ACK tại byte tiếp theo đang chờ; quyết định rõ buffer out-of-order hay drop theo mô hình đã chọn; tuyệt đối không ACK vượt qua gap hoặc giao byte trùng cho ứng dụng.
3. Tách `SendBase` (byte cũ nhất chưa ACK) và `NextSeqNum` (byte tiếp theo để gửi). Hiện `server_seq` bị dùng làm nhiều mốc; phải rà cập nhật ACK để không làm lùi hoặc nhảy sequence state.
4. Xây dựng receive buffer và quảng bá `rwnd` động nếu cần đáp ứng flow control slide 90–95. Cập nhật sender theo window peer; phối hợp với `cwnd` nếu implement congestion control. Các giới hạn gửi theo byte là cách triển khai suy ra từ slides 94 và 122.
5. Thêm congestion control riêng; đừng nhầm RTO/fast retransmit sẵn có với AIMD. Dùng slide 120–125 để mô tả quy tắc; không lấy 64 KB hay MSS 1460 làm mặc định bắt buộc.
6. Rà handshake/FIN và tích hợp HTTP adapter. `accept()` và `close_connection()` đã tồn tại nhưng còn sơ sài; raw send/close đang bị comment ở adapter.
7. Chỉ bổ sung raw `connect()` nếu yêu cầu peer cần chủ động mở kết nối; đánh dấu đây là quyết định kiến trúc/đề bài, không phải yêu cầu tự thân của Chapter 3.

## Các mục trong study guide cần cập nhật

Study guide hiện có các dòng lỗi thời so với source đang nằm cùng thư mục và cần ghi nhận cấu hình nhóm MTU=1500 B, MSS=1460 B:

- Mục 1.4 nói `run_conn_send()` gửi toàn payload trong một segment và chưa có retransmission timer. Source hiện phân đoạn theo `MSS=1300`, có `unacked`, `RttEstimator`, `wait_for_ack()`, timeout và fast retransmit.
- Mục mô tả `run_conn_recv()` chỉ ACK `pkt_seq + len(payload)` mà không kiểm tra sequence. Source hiện có `classify_segment()` và chỉ chấp nhận in-order; vẫn còn vấn đề drop gap/out-of-order và chưa verify checksum.
- Study guide nói chưa có state send buffer/RTO; source có các biến này ở phạm vi từng lần gọi gửi, nhưng chưa gắn đầy đủ vào state lâu dài của connection.
- Mục Flow/Congestion cần giữ kết luận chưa có window động và chưa có `cwnd`; ghi rõ cấu hình nhóm MSS=1460 B, MTU=1500 B. Các slide không bắt buộc đúng con số này; đây là phép tính theo IPv4/TCP header cơ bản.

## Nguồn slide chính

- Slides 30–34: Internet checksum và giới hạn phát hiện lỗi.
- Slides 50–61, 70–75: sequence/ACK, retransmission và buffering trong các mô hình reliable transfer.
- Slides 77–88: TCP byte sequence, cumulative ACK, RTT/RTO, receiver ACK và fast retransmit.
- Slides 90–95: flow control và receive window.
- Slides 96–104: handshake và FIN.
- Slides 120–125: AIMD, `cwnd`, slow start, `ssthresh` và các phản ứng khi loss.
