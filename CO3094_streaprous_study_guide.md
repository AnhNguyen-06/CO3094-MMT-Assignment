# Assignment 1: đối chiếu đặc tả và hướng dẫn hoàn thiện StreapRous

Ngày tổng hợp: **11/11/2026**. Nhóm có **6 thành viên**, chia thành ba cặp; **bạn và Lâm phụ trách Reliability**.

Tài liệu này tổng hợp yêu cầu, kiến thức và vị trí cần hoàn thiện; **không phải bản triển khai thuật toán**. Phạm vi đã thống nhất là **bám raw TCP của framework hiện có**. Trong lượt tạo tài liệu, không chỉnh sửa hoặc chạy framework.

Quy ước bằng chứng:

- **[Đề]**: yêu cầu hoặc mô tả được nêu trong hai đặc tả.
- **[Mã hiện tại]**: hành vi quan sát bằng cách đọc source được cấp, chưa kiểm chứng bằng chạy chương trình.
- **[Đề xuất]**: cách tổ chức công việc hoặc hướng hoàn thiện suy ra từ slide và source; không tự động là yêu cầu riêng của thầy.
- **[Cần xác nhận]**: hai đặc tả chưa thống nhất hoặc chưa đủ rõ để kết luận.
- **[Bổ sung ngoài slide]**: kiến thức từ nguồn bên ngoài, được tách riêng và dẫn nguồn.

Mọi số trang bên dưới là **trang PDF, đếm từ 1**. Trong Chapter 3, trang PDF N khớp số slide `3-N`. Đặc tả StreapRous có **32 trang PDF**: phần đề chính là trang 1–13; trang 14–32 là tài liệu API đính kèm. Không dừng đọc ở dòng chân trang “Page 13 of 13”. Số dòng source là mốc của bản được kiểm tra ngày tổng hợp; khi source thay đổi, tìm theo tên hàm.

## Đối chiếu hai đặc tả và phần thầy đã hỗ trợ

### Nguồn và nguyên tắc đọc

- **Đề cũ**: [Assignment 1 - Distributed Streaming-based Client-Server Collaboration Application](<Assignment 1 - Distributed Streaming-based Client-Server Collaboration Application.pdf>), 4 trang.
- **Đề mới**: [CO3094_assignment_streaprous](CO3094_assignment_streaprous.pdf), 32 trang PDF.
- **Source thực tế**: [CO3094_streaprous](CO3094_streaprous/README.md). Khi tên module, chữ ký hàm hoặc hành vi trong tài liệu API khác source, vị trí sửa trong hướng dẫn này lấy theo source.

| Nội dung | Đề cũ | Đề mới và hỗ trợ của framework |
|---|---|---|
| Sản phẩm | Đăng nhập, discovery, chat broadcast/unicast, truyền file tin cậy, khả năng chịu gián đoạn và bảo mật; tr. 1–2. | HTTP server và chat lai client-server/P2P; tr. 1, 8–11. Có nền proxy/backend/webapp để phát triển tiếp. |
| Transport | Nhấn mạnh UDP streaming và reliability tự bổ sung; đồng thời một số đoạn mô tả TCP; tr. 1–3. | Raw TCP, bắt tay ba bước, ordered byte stream, hàm nhận/gửi; tr. 7–8. Source dựng IP/TCP packet thủ công. |
| Kiến trúc | Tự thiết kế protocol, state diagram và phân tách network/data/UI; tr. 2–3. | Cấp cấu trúc daemon, proxy, backend, route và request/response; tr. 3–8. |
| Chat | Người dùng hoạt động, chat chung và riêng; tr. 1–3. | Tracker nhận IP/port, quản lý danh sách và discovery; peer liên lạc trực tiếp; channel, thông báo, tin nhắn không sửa/xóa; tr. 9–11. |
| Đồng thời | Multithreading hoặc async I/O, hướng tới 10–20 client; tr. 2–3. | Non-blocking giữa các daemon, gợi ý callback/coroutine; JavaScript chỉ phía client; tr. 10. Có skeleton threading/callback/coroutine, mức hoàn thiện khác nhau. |
| Công nghệ | Python/Java/C++/Go; cấm framework networking cấp cao; tr. 3. | Backend Python thư viện chuẩn; cấm JavaScript backend và web framework có sẵn; tr. 10. Sử dụng nền giảng viên đã cấp. |
| Bảo mật | Mã hóa payload bằng thư viện mật mã tiêu chuẩn; tr. 2, 4. | Authentication bằng HTTP headers/cookies và các RFC tham khảo; tr. 8. Cookies không thay thế mã hóa. |
| Chấm điểm | 10 milestone, mỗi mục 1 điểm; tr. 3–4. | Tr. 12, mục 3.2–3.3 vẫn dẫn chiếu yêu cầu và cách chấm của Assignment 1 cũ. |

**[Đề] Hai tài liệu cùng hướng đến giao tiếp nhiều tiến trình, protocol design, quản lý trạng thái, đồng thời, xử lý lỗi và ứng dụng cộng tác.** Điểm hỗ trợ lớn nhất là cấp nền có thể mở rộng và các điểm tích hợp, giúp sinh viên không phải tự dựng mọi thành phần từ đầu.

**[Cần xác nhận] Không có căn cứ để tự coi truyền file, mã hóa, chống Head-of-Line (HoL) blocking hoặc mục tiêu số client đã được miễn.** Đề mới không nhắc lại đầy đủ các mục đó nhưng vẫn dẫn chiếu đề cũ. Tài liệu này chọn raw TCP theo phạm vi nhóm đã thống nhất, không khẳng định lựa chọn đó đã giải quyết mọi mâu thuẫn của đề.

### Thầy đã làm gì trong source?

| Thành phần | Hỗ trợ thực sự có | Phần sinh viên còn phải hoàn thiện |
|---|---|---|
| [Raw connection](CO3094_streaprous/streaprous_socket/streaprous_raw_connection.py) | Dựng IP/TCP header, checksum gửi, accept handshake, bảng connection, gửi/nhận cơ bản, FIN/RST cơ bản. | Reliability đầy đủ, cửa sổ động, congestion control; rà lại handshake và đóng kết nối. Chưa có API chủ động kết nối raw TCP tương ứng `connect()` cho peer. |
| [Packet dispatcher](CO3094_streaprous/streaprous_socket/streaprous_packet_dispatcher.py) | Một thread đọc raw socket, phân phối về queue theo client IP/port trong ngữ cảnh listener hiện có. | Phối hợp xử lý liên tục ACK/data và bộ đệm; queue này chưa phải thuật toán Reliability hoặc Flow Control. |
| [Backend](CO3094_streaprous/daemon/backend.py) | Khởi tạo raw socket, accept và tạo thread handler; có thêm nhánh standard socket/callback/coroutine. | Tích hợp vòng đời transport; kiểm tra nhánh async cần dùng. Mặc định threading chưa chứng minh đáp ứng mọi yêu cầu non-blocking. |
| [HTTP adapter](CO3094_streaprous/daemon/httpadapter.py) | Điểm nhận request, gọi hook, dựng response và tích hợp transport. | Nhánh raw còn TODO gửi/đóng và hook; phải xử lý đúng thông điệp HTTP trên byte stream. |
| [Request](CO3094_streaprous/daemon/request.py), [Response](CO3094_streaprous/daemon/response.py) | Helper tách request, định dạng response, đọc file và MIME. | Parser/cookies/authentication và một số loại response còn chỗ trống. Có TODO đã kèm code thực hiện, vì vậy không dùng số TODO để kết luận mức hoàn thiện. |
| [Proxy](CO3094_streaprous/daemon/proxy.py), [cấu hình](CO3094_streaprous/config/proxy.conf) | Cấu hình host/backend, helper forwarding và routing. | Dispatch client trong accept loop, xử lý policy/error còn thiếu; proxy hiện dùng `SOCK_STREAM`. |
| [Route framework](CO3094_streaprous/daemon/streaprous.py), [sampleapp](CO3094_streaprous/apps/sampleapp.py) | Decorator đăng ký route và handler ví dụ. | Tracker, chat, channel, giao thức peer, truyền file và UI hoàn chỉnh. Sample login chưa phải authentication hoàn chỉnh. |

**[Mã hiện tại] Raw socket dùng `SOCK_RAW`/`IPPROTO_TCP`; việc gắn TCP header không tự cung cấp đầy đủ dịch vụ TCP của hệ điều hành cho phần raw do nhóm xử lý.** Cũng không thể dùng thành công của đường `SOCK_STREAM` tại proxy để chứng minh Reliability raw đã hoàn thiện.

Đề mới có các dấu vết tài liệu khác phiên bản: WeApRous/AsynapRous, tên `ConnectionInfo` so với `conn_struct`, một số thư mục liệt kê ở tr. 3–4 không có trong source hiện tại. Tài liệu API mô tả standard socket cho localhost, nhưng `run_backend()` hiện ném `ValueError` với địa chỉ localhost. Không mặc định mọi ví dụ trong phụ lục chạy được nguyên trạng.

## 1. Reliability — bạn và Lâm

### 1.1. Kết quả cần đạt và ranh giới trách nhiệm

**[Đề xuất]** Trên kết nối đã thiết lập, transport phải cung cấp byte đúng nội dung và đúng thứ tự, không giao trùng cho tầng trên; phát hiện lỗi, khôi phục mất data/ACK và có xử lý kết thúc/lỗi rõ ràng. Đây là hướng áp dụng slide vào framework, không phải một rubric Reliability riêng được thầy công bố.

Reliability giải quyết dữ liệu bị mất/hỏng/trùng/sai thứ tự. Flow Control giới hạn theo sức nhận của peer; Congestion Control giới hạn theo tình trạng mạng. Ba phần dùng chung state và đường ACK, nhưng cần phân công rõ trách nhiệm.

TCP ACK xác nhận **byte đã được transport nhận liên tục**, không chứng minh ứng dụng đã lưu file hoặc thực hiện xong một thao tác chat. Việc hoàn tất file/thông điệp ở tầng ứng dụng cần protocol của ứng dụng.

### 1.2. Bản đồ đầy đủ các slide cần đọc

Nguồn chính: [Chapter_3_v8.0.pdf](../Chapter_3_v8.0.pdf).

| Trang PDF / slide Chapter 3 | Nội dung | Áp dụng vào framework | Ưu tiên |
|---|---|---|---|
| 16–22 | Multiplexing/demultiplexing, TCP 4-tuple. | Hiểu khóa connection và dispatcher; cặp client IP/port hiện chỉ dùng trong ngữ cảnh listener được cố định. | Cần biết |
| 30–34 | Checksum, phép cộng bù một và giới hạn phát hiện lỗi. | Tái sử dụng `checksum()`, bổ sung validation phía nhận. | Cần biết |
| 37–42 | Reliable abstraction, `rdt_send`, `udt_send`, `rdt_rcv`, `deliver_data`, FSM. | Tách sự kiện gửi/nhận/timer và hành động cập nhật state. | Bắt buộc |
| 43–49 | rdt1.0, rdt2.0, ACK/NAK, bit error. | Hiểu phát hiện lỗi và gửi lại; mô hình này chưa đủ xử lý mất gói. | Nền tảng |
| 50–55 | rdt2.1/2.2, sequence number, ACK lỗi, duplicate. | Chống giao dữ liệu trùng; hiểu ACK-only. | Bắt buộc |
| 56–61 | rdt3.0, timer, mất data/ACK, delayed ACK, premature timeout. | Buffer gửi lại và bộ tình huống kiểm chứng. | Bắt buộc |
| 62–66 | Hiệu suất stop-and-wait, pipelining. | Lý do cần nhiều segment in-flight. | Cần biết |
| 67–69; 144–145 | Go-Back-N, cumulative ACK, timer và FSM. | So sánh chính sách gửi lại; không mặc định retransmit cả cửa sổ cho TCP. | So sánh |
| 70–75 | Selective Repeat, buffer sai thứ tự, cửa sổ và không gian sequence. | Hiểu reassembly, chỉ gửi lại phần thiếu và vấn đề số thứ tự quay vòng. | Cần biết |
| 77–80 | TCP overview/header, sequence theo byte, cumulative ACK. | Ánh xạ chính xác `seq`/`ack_seq` của code. | Trọng tâm |
| 81–83 | RTT, EstimatedRTT, DevRTT, timeout. | Tính RTO thay vì chờ tùy ý. | Trọng tâm |
| 84–88; 146 | TCP sender/receiver, ACK generation, retransmission, fast retransmit. | Hướng hoàn thiện `run_conn_send()`/`run_conn_recv()`. | Trọng tâm |
| 96–104; 147 | Connection management, handshake, FIN và FSM. | Rà `accept()` và `close_connection()`. | Bắt buộc khi tích hợp |
| 137–141 | QUIC, nhiều stream và HoL. | Nhận diện giới hạn raw TCP so với yêu cầu UDP streaming của đề cũ. | Đọc để hiểu phạm vi |

**Thứ tự học:** 37–61 → 77–88 → 146 → 65–75 → 96–104, 147. Đọc 30–34 và 16–22 khi xem helper/dispatcher. Các FSM rdt là mô hình học, không phải yêu cầu cài tuần tự tất cả phiên bản trong sản phẩm.

### 1.3. Những kiến thức phải giải thích được

1. **Checksum:** phát hiện một số lỗi, không sửa lỗi và không bảo đảm phát hiện mọi trường hợp; slide 32–34. Checksum không phải cơ chế mã hóa hoặc xác thực bảo mật.
2. **Sequence và duplicate:** retransmission có thể xảy ra khi ACK mất hoặc chỉ đến muộn; receiver không được giao cùng byte lần nữa; slide 50–61.
3. **ACK TCP:** giá trị ACK là số thứ tự byte tiếp theo còn chờ, xác nhận tích lũy toàn bộ phần liên tục trước đó; slide 78–80. Ví dụ GBN/SR dùng ACK theo gói, không được bê nguyên quy ước đó vào TCP header.
4. **SendBase khác NextSeqNum:** byte cũ nhất chưa ACK và byte tiếp theo để gửi là hai mốc khác nhau; slide 79, 84, 146. Gửi xuống socket thành công chưa chứng minh peer đã nhận.
5. **Gap và in-order delivery:** gói đến sau không làm phần thiếu biến mất; có thể buffer out-of-order nhưng chỉ giao phần liên tục cho tầng trên; slide 70–73, 79, 85.
6. **Timer và fast retransmit:** timer phục vụ khôi phục mất gói; ba duplicate ACK bổ sung là tín hiệu gửi lại segment chưa ACK có sequence nhỏ nhất theo slide 88. Không gửi lại trên mọi duplicate ACK như mô hình rdt2.2 đơn giản.
7. **TCP là byte stream:** không có ranh giới message; slide 77. Một lần nhận có thể chỉ là một phần HTTP request hoặc chứa dữ liệu của nhiều phần ứng dụng.
8. **Handshake/FIN:** ACK cuối của handshake có thể kèm data; slide 101. Đóng kết nối là quá trình trao đổi trạng thái, không chỉ gửi FIN rồi xóa ngay; slide 103–104.

Các công thức ở slide 82–83:

```text
EstimatedRTT = (1 - α) × EstimatedRTT + α × SampleRTT
DevRTT       = (1 - β) × DevRTT + β × |SampleRTT - EstimatedRTT|
RTO          = EstimatedRTT + 4 × DevRTT

α thường dùng = 0.125
β thường dùng = 0.25
```

Slide 81 nêu không lấy SampleRTT từ retransmission. Các giá trị RTO khởi tạo, giới hạn và chính sách retry cụ thể chưa được chốt trong hướng dẫn nghiên cứu này; không xem công thức trên là toàn bộ đặc tả TCP timer.

### 1.4. Đọc và dự kiến sửa phần nào?

File chính: [streaprous_socket/streaprous_raw_connection.py](CO3094_streaprous/streaprous_socket/streaprous_raw_connection.py).

| Hàm / dòng hiện tại | [Mã hiện tại] | [Đề xuất] phần phải hoàn thiện | Slide |
|---|---|---|---|
| `conn_struct`, `connections`, khoảng 43–60 | Có địa chỉ, state, `server_seq`, `client_seq`, `expected_final_ack`, `last_activity`; chưa có send buffer/RTO. | Tách mốc gửi/ACK/nhận; lưu dữ liệu chưa ACK, thông tin timer/RTT và buffer nhận cần thiết. State phải riêng từng connection. | 79, 81–84, 146 |
| `checksum()`, 127; `build_tcp_packet()`, 144; `send_tcp_data_segment()`, 230 | Tính checksum cho gói gửi. | Kiểm tra tính hợp lệ/checksum gói nhận trước khi tin vào data, ACK hay thay đổi state; tái sử dụng builder khi retransmit. | 30–34, 44–45, 78 |
| `run_conn_send()`, 770 | Gửi toàn payload trong một segment, tăng `server_seq` sau gửi. | Phân đoạn theo MSS phù hợp; lưu phần chưa ACK; xử lý ACK mới, timeout và retransmission; phối hợp ngân sách gửi với hai nhóm còn lại. | 65–66, 77, 79, 84–88, 146 |
| `run_conn_recv()`, 617 | Với data, ACK bằng `pkt_seq + len(app_payload)` rồi trả payload ngay; chưa so với byte đang chờ. | Phân loại in-order/duplicate/out-of-order; chỉ ACK phần liên tục; buffer gap nếu chọn chính sách đó; không giao trùng hoặc giao vượt gap. | 50–61, 70–73, 79, 85 |
| Nhánh pure ACK, khoảng 752–760 | Gán thẳng `server_seq = pkt_ack`; ACK kèm data chưa được xử lý như một sự kiện xác nhận gửi độc lập. | Kiểm tra ACK so với dữ liệu thực sự đã gửi; cập nhật SendBase mà không làm lùi NextSeqNum; xử lý ACK trên cả segment có data khi phù hợp. | 77, 79–80, 84, 146 |
| `accept()`, 370 | Có SYN/SYN-ACK/ACK, timeout 10 giây; chưa so sánh ACK cuối với `expected_final_ack`; trả connection sau khi thấy cờ phù hợp. | Rà validation/state, mất/lặp handshake và data kèm ACK cuối. Tái sử dụng nền đã có. | 96–101, 147 |
| `close_connection()`, 817; nhánh FIN trong receive | Gửi FIN rồi xóa connection/queue; nhận FIN cũng xóa state sau ACK. | Phối hợp dữ liệu chưa ACK với FSM đóng kết nối; giữ state đủ lâu cho quá trình đóng và xử lý lỗi. | 103–104 |

**Ví dụ lỗi gap:** receiver đang chờ byte 100; nhận `seq=200`, payload dài 100 byte. Code hiện có tính ACK 300 dù byte 100–199 còn thiếu. Hướng đúng là chưa ACK vượt gap; cách lưu hoặc bỏ phần đến sau phải nhất quán với chính sách receiver.

**Lưu ý state:** `conn_struct` là namedtuple, code cập nhật bằng `_replace()` trong dictionary. `conn_info` truyền vào handler có thể là bản chụp cũ. Khi mở rộng, phải thống nhất nơi giữ state hiện hành và cách khóa; tránh ghi đè cập nhật của thread khác bằng một bản session cũ.

### 1.5. Tích hợp dispatcher và HTTP

- [streaprous_packet_dispatcher.py](CO3094_streaprous/streaprous_socket/streaprous_packet_dispatcher.py), `_packet_dispatcher()` dòng 41 và `get_packet_queue()` dòng 127: giữ vai trò phân phối gói. Cần thống nhất thành phần tiêu thụ từng queue; không để sender và receiver lấy mất sự kiện của nhau.
- [httpadapter.py](CO3094_streaprous/daemon/httpadapter.py), `handle_client_raw()` dòng 148: gọi receive một lần ở dòng 168; lời gọi `run_conn_send()` và `close_connection()` tại khoảng 192–202 đang bị comment. `sleep(5)` không chứng minh response đã được ACK.
- **Vấn đề vòng đời:** `run_conn_recv()` trả về khi gặp payload đầu tiên; đường handler hiện tại không tiếp tục đọc ACK của response sau đó. Chỉ thêm timer/send buffer là chưa đủ nếu ACK không được xử lý liên tục.
- [backend.py](CO3094_streaprous/daemon/backend.py), `handle_client_raw()` dòng 106 và `run_backend()` dòng 166: là điểm nối socket/connection vào handler, cần phối hợp vòng đời transport.
- HTTP phải gom đủ request theo cấu trúc header/body trước khi parse. Reliability giao byte liên tục; tầng HTTP xác định ranh giới thông điệp, tránh giả định một segment bằng một request.

### 1.6. Phân công đề xuất cho bạn và Lâm

| Vai trò trong cặp | Công việc | Bằng chứng bàn giao |
|---|---|---|
| Người phụ trách sender | Phân đoạn, SendBase/NextSeqNum, buffer chưa ACK, xử lý ACK, timer, RTT/RTO và retransmission. | State/event diagram; log ACK/timeout/gửi lại; tình huống mất data và mất ACK. |
| Người phụ trách receiver | Kiểm tra gói, byte mong đợi, duplicate/out-of-order, cumulative ACK, giao byte liên tục. | Ví dụ gap/duplicate; kiểm tra output byte đúng thứ tự, không lặp. |
| Cả hai | Thống nhất shared state/lock, handshake/FIN, đường tiêu thụ ACK; tích hợp với Flow/Congestion và HTTP. | Luồng dữ liệu/ACK thống nhất, tình huống nhiều connection và đóng kết nối. |

Không mặc định ai là sender hay receiver; hai bạn có thể nhận vai trò theo sở trường. Chốt interface/state chung trước khi sửa cùng file.

### 1.7. Ma trận kiểm chứng khi triển khai sau này

| Tình huống | Kết quả mong đợi | Kiến thức |
|---|---|---|
| Không mất gói, payload nhiều segment | Nhận đủ byte, đúng thứ tự; ACK tích lũy và buffer gửi được giải phóng. | 77–84, 146 |
| Mất một data segment | Có retransmission; không mất phần dữ liệu cuối. | 56–60, 84, 88 |
| Mất ACK nhưng data đã nhận | ACK sau có thể bao phủ ACK mất; khi phải retransmit, receiver không giao trùng. | 61, 86–87 |
| ACK trễ / timeout sớm | Không hỏng output và không làm state gửi lùi. | 61, 81–83, 86 |
| Data trùng, đảo thứ tự, có gap | Không giao trùng; không ACK hoặc giao dữ liệu vượt gap. | 50–55, 70–73, 79, 85 |
| Gói lỗi checksum / header không hợp lệ | Không giao payload lỗi hoặc cập nhật state theo ACK không đáng tin. | 30–34, 44–45, 78 |
| ACK cũ / ACK vượt dữ liệu đã gửi | Không làm sai SendBase/NextSeqNum. | 79, 84, 146; áp dụng kiểm tra state |
| ACK kèm data | Cả sự kiện xác nhận gửi và nhận byte đều được xử lý phù hợp. | 77, 80 |
| Ba duplicate ACK bổ sung | Quan sát fast retransmit segment thiếu; tránh hai thành phần cùng gửi lại. | 88 |
| ACK cuối handshake kèm data | Không mất payload đầu kết nối. | 101 |
| Nhiều connection | State, buffer và timer không lẫn giữa các client. | 20–22, 96 |
| FIN khi còn byte chưa ACK; peer ngắt/RST | Không báo hoàn tất giả hoặc âm thầm bỏ dữ liệu; cleanup không treo. | 103–104; yêu cầu resilience ở đề cũ |

Các mục này là kế hoạch kiểm chứng, **chưa được chạy**. Với lỗi/mất kết nối kéo dài, phải kết thúc hoặc báo lỗi rõ ràng; không thể hứa truyền thành công nếu đường truyền không phục hồi.

## 2. Flow Control — cặp thành viên thứ hai

### 2.1. Slide cần học

Nguồn: [Chapter 3](../Chapter_3_v8.0.pdf).

| Trang PDF / slide | Nội dung | Áp dụng |
|---|---|---|
| 77–79 | Byte stream, header receive window và sender window. | Dùng đơn vị byte; phân biệt byte đã ACK và đang in-flight. |
| 90–93 | Receiver nhận nhanh hơn ứng dụng đọc; mục tiêu bảo vệ bộ đệm. | Xác định lúc nào dữ liệu còn chiếm chỗ và lúc nào được giải phóng. |
| 94–95 | Quảng bá `rwnd`, giới hạn dữ liệu chưa ACK. | Cửa sổ động phía nhận; sender tuân thủ cửa sổ peer. |
| 65–75 | Pipelining, sender/receiver buffering. | Bổ trợ; cửa sổ ARQ không tự động là receive window TCP. |
| 122 | Giới hạn `cwnd`. | Phối hợp với Congestion Control. |

### 2.2. File và phần cần hoàn thiện

File chính vẫn là [streaprous_raw_connection.py](CO3094_streaprous/streaprous_socket/streaprous_raw_connection.py); phối hợp [dispatcher](CO3094_streaprous/streaprous_socket/streaprous_packet_dispatcher.py) và [HTTP adapter](CO3094_streaprous/daemon/httpadapter.py).

| Vị trí | [Mã hiện tại] | [Đề xuất] |
|---|---|---|
| `build_tcp_packet()`, dòng 144; `send_tcp_data_segment()`, dòng 230 | `window = 5840` cố định tại dòng 160 và 251. | Cho phép đưa receive window thực tế vào mọi gói cần quảng bá, gồm gói ACK/control phù hợp. |
| `conn_struct` / state connection | Chưa có dung lượng buffer hoặc `peer_rwnd`. | Lưu dung lượng, byte đang chiếm, advertised window và cửa sổ peer theo từng connection. |
| `run_conn_recv()`, dòng 617 | Unpack header nhưng chưa dùng trường window của peer để giới hạn gửi. | Đọc/cập nhật peer window; phối hợp receiver Reliability quản lý dung lượng. |
| `run_conn_send()`, dòng 770 | Chưa hạn chế in-flight theo receive window. | Chỉ gửi dữ liệu mới khi còn ngân sách nhận và congestion budget. |
| Dispatcher `get_packet_queue()`, dòng 127 | `Queue(maxsize=100)` giới hạn số phần tử. | Không coi 100 packet là 100 byte hoặc là toàn bộ TCP receive buffer. Theo dõi byte ở nơi dữ liệu thực sự được lưu. |
| HTTP adapter đọc dữ liệu | Chưa có luồng đọc/giải phóng receive buffer hoàn chỉnh. | Khi ứng dụng lấy dữ liệu, cập nhật bộ đệm và quảng bá cửa sổ phù hợp. |

### 2.3. Quan hệ cần nắm và giao điểm với Reliability

Từ slide 94–95:

```text
rwnd ≈ dung lượng bộ đệm nhận - lượng dữ liệu đang chiếm
```

**[Đề xuất suy ra từ slide 94–95 và 122]** Khi dùng cùng đơn vị byte:

```text
bytes_in_flight ≈ NextSeqNum - SendBase
ngân sách gửi dữ liệu mới ≈ max(0, min(peer_rwnd, cwnd) - bytes_in_flight)
```

Đây là mô hình kế toán cho dữ liệu trên kết nối đã thiết lập; không phải công thức bao quát SYN/FIN và sequence wraparound. Không tính retransmission thành dữ liệu mới để tăng NextSeqNum lần nữa.

Dữ liệu out-of-order đã giữ và dữ liệu in-order chưa giao ứng dụng đều chiếm bộ đệm; thống nhất cách đếm để không tính trùng. Reliability cập nhật byte đã ACK; Flow Control cập nhật sức nhận. Một ACK có thể chỉ cập nhật window mà không xác nhận thêm byte mới.

### 2.4. Phân công và kiểm chứng

- Một người phụ trách receive buffer, tính/quảng bá `rwnd` và cập nhật khi ứng dụng đọc.
- Người còn lại phụ trách `peer_rwnd`, chặn/tiếp tục gửi và tích hợp ngân sách gửi chung.
- Kiểm chứng ứng dụng đọc chậm, buffer gần đầy, window về 0, window mở lại, out-of-order chiếm buffer và window update không kèm ACK tiến thêm.
- Tiêu chí: không tràn bộ đệm; dừng gửi dữ liệu mới khi hết ngân sách; tiếp tục khi có cập nhật hợp lệ; không làm sai state Reliability.

**Giới hạn kiến thức:** slide 90–95 không trình bày đầy đủ cơ chế TCP zero-window recovery/persist timer. Trường hợp mất window update cần được ghi nhận khi triển khai; không tuyên bố công thức `rwnd` tự giải quyết được tình huống đó. Hướng dẫn hiện tại chưa thêm nguồn ngoài cho cơ chế này.

## 3. Congestion Control — cặp thành viên thứ ba

### 3.1. Slide cần học

Nguồn: [Chapter 3](../Chapter_3_v8.0.pdf).

| Trang PDF / slide | Nội dung | Mục đích |
|---|---|---|
| 106–118 | Nguyên nhân/chi phí congestion, loss/delay, end-to-end và network-assisted. | Phân biệt nghẽn mạng với receiver chậm. |
| 120–122 | AIMD, `cwnd`, in-flight và tốc độ gửi. | Giới hạn sender bằng trạng thái mạng. |
| 123–125 | Slow start, congestion avoidance, `ssthresh`, fast recovery, FSM. | Nền tảng sự kiện ACK/timeout/duplicate ACK. |
| 126–127 | CUBIC, `Wmax`, mốc `K`, tăng theo thời gian. | Thuật toán phù hợp để nghiên cứu tiếp theo đề cũ. |
| 128–131 | Bottleneck, RTT, delay-based control; giới thiệu BBR. | Giải thích đo đạc và giới hạn thông tin về BBR trong slide. |
| 132 | ECN. | Đọc bổ trợ; chưa mặc định phải bổ sung ECN. |
| 133–135 | Fairness, ảnh hưởng nhiều kết nối. | Đánh giá hai luồng cạnh tranh. |
| 148–149 | Throughput, RTT, đường truyền lớn/xa. | Bổ trợ phân tích hiệu suất. |

### 3.2. File và phần cần hoàn thiện

File chính: [streaprous_raw_connection.py](CO3094_streaprous/streaprous_socket/streaprous_raw_connection.py). Điểm nối là state connection, `run_conn_send()` và đường xử lý ACK/timeout của Reliability; [backend](CO3094_streaprous/daemon/backend.py) và [adapter](CO3094_streaprous/daemon/httpadapter.py) phục vụ tích hợp.

| Thành phần | [Mã hiện tại] | [Đề xuất] |
|---|---|---|
| State mỗi connection | Chưa có `cwnd`, `ssthresh`, congestion controller. | Lưu trạng thái riêng cho từng connection, thống nhất đơn vị byte/MSS. |
| Đường gửi `run_conn_send()` | Gửi payload một lần, không có congestion budget. | Chỉ gửi dữ liệu mới trong ngân sách `min(peer_rwnd, cwnd)` sau khi trừ in-flight. |
| Đường ACK | Chưa có sự kiện controller. | Reliability phân loại ACK mới/duplicate và chuyển thông tin cần thiết cho controller. |
| Đường timeout | Chưa có retransmission timer. | Reliability xác định timeout; controller điều chỉnh cửa sổ; thống nhất bên thực hiện gửi lại. |
| Đo đạc | Có log gói cơ bản, chưa có chỉ số controller. | Ghi thời gian, connection, `cwnd`, RTT, byte được ACK, loss/timeout và retransmission. |

Reliability chịu trách nhiệm bảo toàn dữ liệu và gửi lại. Congestion Control quyết định điều chỉnh tốc độ/cửa sổ. Không để cả hai bên xử lý cùng một sự kiện bằng hai lần retransmit.

### 3.3. Chọn thuật toán và nguồn ngoài được dùng

**[Đề]** Đề cũ tr. 2 nêu BBR/CUBIC; đề mới tr. 12 dẫn chiếu yêu cầu cũ. Không tự kết luận Reno là đủ sản phẩm cuối cùng. Dùng slide 120–125 để hiểu và kiểm chứng cơ chế nền trước.

**[Đề xuất]** Nếu nhóm cần đáp ứng lựa chọn BBR/CUBIC, hướng nghiên cứu là **CUBIC**: slide 126–127 giới thiệu trực tiếp; slide 131 chỉ giới thiệu BBR ở mức khái quát. Không triển khai BBR trong lượt nghiên cứu/tạo tài liệu này.

**[Bổ sung ngoài slide — nguồn duy nhất đã sử dụng]** [RFC 9438: CUBIC for Fast and Long-Distance Networks, mục 4](https://www.rfc-editor.org/rfc/rfc9438.html#section-4), từ IETF/RFC Editor.

Lý do cần nguồn ngoài: slide 126–127 có ý tưởng nhưng chưa đủ các bước và tham số để triển khai CUBIC. Đọc mục 4.1–4.8 để tra biến, hàm tăng cửa sổ, Reno-friendly region, giảm cửa sổ và timeout. RFC dùng cửa sổ theo segment SMSS; nếu code dùng byte phải quy đổi theo MSS. Không gán các chi tiết bổ sung này cho slide của thầy.

Hướng dẫn này chưa sao chép toàn bộ thuật toán RFC hoặc tự chọn thêm tham số CUBIC. Khi triển khai phải chỉ rõ phần nào theo slide, phần nào theo RFC và giới hạn của bản làm; không gọi một hàm tăng cửa sổ đơn giản là CUBIC hoàn chỉnh.

### 3.4. Phân công và kiểm chứng

- Một người phụ trách controller/state và quy tắc cập nhật cửa sổ theo ACK/loss.
- Người còn lại phụ trách tích hợp ngân sách gửi, đo đạc, log và thí nghiệm bottleneck/fairness.
- Kiểm chứng ACK đều khi không mất gói, timeout, duplicate ACK, bottleneck, hai luồng cạnh tranh và receiver chậm.
- Tiêu chí: quan sát được điều chỉnh cửa sổ theo controller; mất gói không gây hai lần gửi lại từ hai module; phân biệt được giới hạn do `cwnd` với giới hạn do `rwnd`.

## Kiến thức bổ trợ và phối hợp toàn nhóm

### Các Chapter khác nên đọc

| Tài liệu | Trang PDF | Cần dùng vào đâu |
|---|---|---|
| [Chapter 1](../Chapter_1_v8.0.pdf) | 51–62; 74–75; 85 | Delay/loss/throughput, phân tầng và Wireshark. Giúp giải thích thí nghiệm, không thay thuật toán Chapter 3. |
| [Chapter 2](../Chapter_2_v8.0.pdf) | 7–17; 20–36; 43–48; 75–83; 103–112 | Client-server/P2P, protocol design, HTTP/cookies, HoL, tracker/chunk và socket. Reliability ưu tiên 10–15, 27–30, 103–112. |
| [Chapter 4](../Chapter_4_v8.0.pdf) | 43; 95–96; 100–101 | IP header, end-to-end argument, MTU và fragmentation. TCP segmentation và IP fragmentation là hai cơ chế khác nhau. |
| [Chapter 6](../Chapter_6_v8.0.pdf) | 6–7; 11–15; 58 | Reliability link-level, checksum/CRC, Ethernet không tự bảo đảm end-to-end delivery. Không thay checksum TCP bằng CRC Ethernet. |
| [Chapter 8](../Chapter_8_v8.0.pdf) | 4; 15; 44–45; 58–69 | Mã hóa, integrity, TLS. Dành cho yêu cầu bảo mật toàn bài; checksum Reliability không cung cấp bảo mật mật mã. |

Đã rà các chương còn lại để tìm phần liên quan. Chapter 5 về control plane/routing và Chapter 7 về wireless/mobile không phải trọng tâm thuật toán của ba phần transport đang phân công; không cần học hết chúng trước khi bắt đầu Reliability. Chỉ quay lại khi môi trường thí nghiệm phát sinh vấn đề routing/wireless tương ứng.

### Ba tài liệu CO3094 - Lab có thể tận dụng

| Tài liệu | Trang PDF | Nội dung liên quan |
|---|---|---|
| [Lab 1 — Network Device](<../Lab/CO3094 -Lab1-Network Device.pdf>) | 3–6; 8 | Dựng testbed, DHCP/IP/ping, capture HTTP và chạy client/server. |
| [Lab 2 — Subnet with DHCP DNS and HTTP](<../Lab/CO3094 - Lab2 - Subnet with DHCP DNS and HTTP v2.pdf>) | 1–2; 5–7, đặc biệt 6–7 | Tracker bước đầu; Wireshark xem Seq/ACK, SYN/ACK/FIN, retransmission, RTT, throughput và Follow TCP Stream. |
| [Lab 3 — Interconnected network](<../Lab/CO3094 - Lab3 - Interconnected network v6.pdf>) | 1; 5–8 | `get_list()`, `peer_connect()`, peer server/client; dựng và kiểm tra liên thông giữa subnet. |

Lab giúp dựng/quan sát thí nghiệm, không thay thế cơ chế rdt/TCP trong Chapter 3. Khi Lab dùng từ “fragmented TCP packet”, đối chiếu Chapter 3 và Chapter 4 để phân biệt segmentation và IP fragmentation. Không suy ra UDP có sequence number sẵn chỉ từ câu hỏi quan sát packet loss ở Lab.

### Những phụ thuộc ngoài ba thuật toán cần giao người xử lý

| File / điểm vào | Hiện trạng cần lưu ý | Trách nhiệm phù hợp |
|---|---|---|
| [daemon/request.py](CO3094_streaprous/daemon/request.py), `prepare()` dòng 107 | Phần gán `_raw_headers`, `_raw_body`, `headers` còn trống nhưng dòng 125 đã dùng `_raw_headers`; có thể lỗi trước khi demo HTTP tới được đường gửi. | HTTP/parser chung; cần xử lý để kiểm chứng end-to-end, không phải thuật toán Reliability. |
| [daemon/httpadapter.py](CO3094_streaprous/daemon/httpadapter.py), `handle_client_raw()` dòng 148 | Gửi raw/close bị comment, hook còn TODO; mới nhận một chunk. | Người tích hợp HTTP phối hợp cặp Reliability. |
| [daemon/backend.py](CO3094_streaprous/daemon/backend.py) | Khởi tạo transport và handler; có các nhánh đồng thời khác nhau. | Vòng đời connection và tích hợp non-blocking. |
| [daemon/proxy.py](CO3094_streaprous/daemon/proxy.py), `run_proxy()` dòng 174 | Accept loop thiếu dispatch xử lý client; policy/error handling còn thiếu. | Proxy/HTTP chung; không tính toàn bộ vào Reliability. |
| [start_backend.py](CO3094_streaprous/start_backend.py), `setup_rst_block()` | Có thao tác firewall để chặn RST của kernel khi chạy. README hướng đến môi trường Linux có quyền phù hợp. | Chuẩn bị môi trường thí nghiệm sau; lượt này không chạy script hoặc đổi firewall. |
| [apps/sampleapp.py](CO3094_streaprous/apps/sampleapp.py) | Route mẫu, chưa có toàn bộ tracker/chat/channel/file. | Phần ứng dụng toàn nhóm. |

### Hợp đồng phối hợp trước khi sửa source

**[Đề xuất]** Không chia quyền sở hữu chỉ theo file vì cả ba cặp đều đụng `streaprous_raw_connection.py`. Cần thống nhất trước:

| Dữ liệu / sự kiện | Bên chịu trách nhiệm chính | Bên sử dụng |
|---|---|---|
| `SendBase`, `NextSeqNum`, byte đã ACK/in-flight, retransmission buffer | Reliability sender | Flow Control, Congestion Control |
| Byte nhận tiếp theo, gap/duplicate, dữ liệu đủ thứ tự | Reliability receiver | HTTP/ứng dụng, Flow Control |
| Dung lượng/occupancy nhận, advertised window, `peer_rwnd` | Flow Control | Reliability sender và ngân sách gửi |
| `cwnd`, `ssthresh`, trạng thái controller | Congestion Control | Đường gửi chung |
| ACK mới, duplicate ACK, timeout, mẫu RTT phù hợp | Reliability phân loại/phát hiện | Congestion Control; Flow Control đọc window update |
| Chính sách bắt tay/đóng, cleanup và báo lỗi | Reliability phối hợp tích hợp backend | Các buffer/controller và ứng dụng |

Giữ các điểm vào `accept()`, `run_conn_recv()`, `run_conn_send()` và `close_connection()` làm mốc tích hợp. Tài liệu nghiên cứu này chưa chốt việc thay chữ ký hàm hoặc type công khai; nếu mở rộng state/builder phải rà toàn bộ nơi gọi và ghi rõ nghĩa kết quả gửi: đã tiếp nhận để gửi hay đã được peer ACK.

### Những điểm chưa thể khẳng định từ tài liệu

- Raw TCP được chọn làm hướng làm việc, nhưng chênh lệch với UDP streaming của đề cũ vẫn cần thầy xác nhận khi chốt phạm vi nộp.
- Raw TCP ordered stream không tự đạt lợi ích nhiều stream tránh HoL như QUIC; xem Chapter 2 tr. 44–48 và Chapter 3 tr. 137–141.
- Chưa có xác nhận miễn truyền file, mã hóa, mục tiêu concurrent client hoặc đổi rubric; tr. 12 đề mới vẫn dẫn chiếu đề cũ.
- Các con số retry, kích thước buffer, MSS môi trường và chính sách hoàn thiện TCP ngoài phần slide chưa được tự chọn trong tài liệu nghiên cứu.
- Yêu cầu backend “thư viện chuẩn” và dependency `netifaces` đang có trong framework cần được hiểu trong ngữ cảnh source thầy cấp; không tự sửa dependency trong lượt này.

### Phạm vi đã thực hiện và cách dùng tài liệu

Chỉ đọc đặc tả, slide, ba tài liệu Lab và source để tổng hợp; bổ sung duy nhất nguồn RFC CUBIC đã ghi ở mục 3.3. Không triển khai ba thuật toán, không chạy test mạng, không khởi động server và không chỉnh framework.

Với bạn và Lâm, bắt đầu bằng mục **1.2–1.4**, sau đó cùng nhóm thống nhất bảng shared state ở trên. Bộ tình huống tại **1.7**, **2.4** và **3.4** là tiêu chí kiểm chứng cho giai đoạn triển khai tiếp theo, không phải báo cáo các test đã chạy.
