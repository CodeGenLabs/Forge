# CONSTITUTION.md — Bản Hiến pháp Kỹ nghệ Forge

Tài liệu chi phối tối cao về mặt nguyên tắc kỹ thuật của **Forge**.

Bản hiến pháp này ràng buộc hai phương diện:
1. **Kiến trúc nội tại của chính Forge:** Những gì được phép xây dựng và những gì kiên quyết từ chối.
2. **Kỷ luật kỹ nghệ áp dụng cho dự án:** Những gì Forge yêu cầu và bắt buộc đối với bất kỳ codebase nào đặt dưới sự giám sát của nó.

---

## Cấu trúc chuẩn mực của một Nguyên tắc

Một nguyên tắc mà không có cơ chế phát hiện vi phạm thì chỉ là một lời nguyện vọng mang tính hình thức. Do đó, mỗi nguyên tắc trong bản Hiến pháp này đều mang đúng 4 trường thông tin bắt buộc:

| Trường | Ý nghĩa |
|---|---|
| **Quy tắc (Rule)** | Tuyên bố chuẩn mực: BẮT BUỘC (MUST) / KHÔNG ĐƯỢC PHÉP (MUST NOT) / NÊN (SHOULD). |
| **Lý do (Why)** | Cơ sở lý luận kỹ thuật và bằng chứng thực tế chứng minh tính cần thiết. |
| **Cơ chế (Mechanism)** | Thành phần chịu trách nhiệm phát hiện vi phạm: Kernel check, Cổng kiểm soát (Gate), hay sự phê duyệt của con người. |
| **Miễn trừ (Waiver)** | Cách thức bỏ qua ngoại lệ một cách minh bạch, có thời hạn và chi phí đánh đổi. |

---

## 16 NGUYÊN TẮC KỸ NGHỆ CỐT LÕI

### I. Xác định trước, Xác suất sau (Deterministic before probabilistic)
- **Quy tắc:** Bất kỳ phép kiểm tra nào *có thể* viết thành một script xác định thì BẮT BUỘC phải là script. Mô hình ngôn ngữ (LLM) KHÔNG ĐƯỢC PHÉP là thẩm quyền duy nhất cho bất kỳ cổng kiểm soát (gate) nào. Việc chuyển một kiểm tra từ sự phán đoán cảm tính của AI sang mã lệnh bằng cách đặt quy ước ID, bổ sung trường dữ liệu hoặc gắn anchor luôn luôn là một cải tiến và BẮT BUỘC phải được ưu tiên hơn việc tối ưu hóa prompt.
- **Lý do:** Ràng buộc dựa trên prompt luôn có thể bị AI lách luật hoặc giải thích bao biện khi ngữ cảnh dài. Máy tính đếm ID và kiểm tra cú pháp chính xác 100%; AI thì có thể đếm sai và ảo giác.
- **Cơ chế:** Mã thoát (Exit code) của lệnh `forge gate` là thẩm quyền chặn (blocking authority) duy nhất.
- **Miễn trừ:** Không có. Đây là nguyên tắc nền tảng của Forge.

---

### II. Khảo sát trước khi sửa; Tái hiện trước khi sửa lỗi (Investigate before modifying; reproduce before fixing)
- **Quy tắc:** Không thực hiện bất kỳ hành động viết code nào trước khi hiện trạng liên quan được đọc và nêu rõ. Không sửa bug trước khi có một bài test tái hiện lỗi được commit ở trạng thái thất bại (failing test). Phải tìm ra nguyên nhân gốc rễ trước khi đưa ra biện pháp khắc phục — việc chỉ sửa triệu chứng bên ngoài là một thất bại kỹ thuật.
- **Lý do:** Khi chưa hiểu rõ hiện trạng, việc sửa code của AI chỉ là phỏng đoán may rủi và thường làm gãy các logic ngầm xung quanh.
- **Cơ chế:** Đồ thị DAG của quy trình `bugfix` bắt buộc phải có artifact `reproduce` trước khi chuyển sang `tasks`. Cổng kiểm soát tại `implement:pre` sẽ chặn nếu thiếu test tái hiện lỗi.
- **Miễn trừ:** Track A (Probe) có thể bỏ qua độ sâu điều tra nhưng không bỏ qua bước khảo sát. Một bugfix không bao giờ được miễn trừ test tái hiện lỗi.

---

### III. Đặc tả trước khi triển khai (Specification before implementation)
- **Quy tắc:** Mọi thay đổi làm biến đổi hành vi nghiệp vụ quan sát được BẮT BUỘC phải có một bản đặc tả delta (`spec/`) với ít nhất một kịch bản kiểm thử cho mỗi yêu cầu. Thay đổi nào không làm đổi hành vi BẮT BUỘC phải khai báo `skip_spec: true` kèm lý do cụ thể. Thứ co giãn theo sự đơn giản là *kích thước của artifact*, tuyệt đối không phải là *sự phê duyệt*.
- **Lý do:** Phát triển phần mềm không có đặc tả sẽ khiến hệ thống không ai biết nó đã cam kết những gì. Bắt buộc viết đặc tả giúp biến ý định thành các tiêu chí nghiệm thu rõ ràng.
- **Cơ chế:** Cổng kiểm soát `spec:post`: kiểm tra cú pháp chuẩn, ≥ 1 kịch bản cho mỗi yêu cầu `REQ-`, từ chối spec rỗng trừ khi có khai báo `skip_spec`.
- **Miễn trừ:** Ghi nhận `skip_spec: true` kèm lý do trong `.forge.yaml` của change.

---

### IV. Lưu trữ phán đoán; Phái sinh dữ kiện (Store judgements; derive facts)
- **Quy tắc:** Một dữ kiện KHÔNG ĐƯỢC lưu trữ thủ công trong tri thức hệ thống nếu một kỹ sư có thể đọc và trích xuất lại nó từ mã nguồn chuẩn mực. Bố cục thư mục, phiên bản package, danh sách API export, đồ thị phụ thuộc và danh mục test đều phải được phái sinh tự động bằng script (`derived/`). Tri thức hệ thống chỉ lưu trữ những gì code không thể tự nói lên: trách nhiệm, ý định nghiệp vụ, bất biến, cạm bẫy và lý do thiết kế.
- **Lý do:** Mọi tài liệu lưu trữ dữ kiện tĩnh (như danh sách file, bảng API tự gõ) đều sẽ mục rữa ngay tại commit tiếp theo khi code thay đổi.
- **Cơ chế:** Lệnh `forge check` tự động phát hiện các mùi: claim có thể phái sinh (derivable-claim smell), liệt kê thư mục thủ công (directory-listing smell), ghi cứng phiên bản thư viện (stack-fact smell).
- **Miễn trừ:** Khai báo `# forge:not-derivable <reason>` trên claim nếu có lý do ngoại lệ được ghi nhận.

---

### V. Mọi Claim đều được neo, gắn nhãn và có bằng chứng (Anchored, labelled, evidenced)
- **Quy tắc:** Mọi Claim được lưu trữ BẮT BUỘC phải có một ID ổn định, một nguồn chân lý (`truth-source`), và ít nhất một neo (`anchor`) trỏ vào code (trừ loại `constraint` ngoài repo hoặc `concept` chung). Một claim được đánh dấu `status: enforced` BẮT BUỘC phải có bằng chứng kiểm thử (`evidence`) chỉ rõ bài test hoặc kiểm tra cơ học sẽ thất bại nếu claim bị vi phạm.
- **Lý do:** Một claim không có neo sẽ không bao giờ có thể kiểm tra tự động và sẽ âm thầm mục rữa. Neo AST mang lại khả năng phát hiện lỗi thời cơ học mà không tốn token AI.
- **Cơ chế:** Lệnh `forge check --scope store` kiểm tra sự hiện diện của anchor, tính hợp lệ của các trường dữ liệu và xác nhận bài test trong evidence đang chạy pass.
- **Miễn trừ:** Claim có thể để trạng thái `asserted` (khẳng định tin là đúng nhưng chưa có test tự động) thay vì `enforced`.

---

### VI. Không bao giờ âm thầm đối soát tài liệu theo code (Never silently reconcile)
- **Quy tắc:** Forge TUYỆT ĐỐI KHÔNG chứa bất kỳ tính năng nào tự động sửa lại tài liệu tri thức cho khớp với code bừa bãi. Khi phát hiện độ lệch (drift), hệ thống BẮT BUỘC phải phân loại vào 1 trong 4 phán quyết (V1: Code sai, V2: Claim sai, V3: Quyết định kiến trúc đổi - cần ADR, V4: Claim thiếu chi tiết). AI có thể đề xuất, nhưng CHỈ CON NGƯỜI mới có quyền phê duyệt phán quyết.
- **Lý do:** Việc tự động sửa tài liệu theo code sẽ biến mọi bug vô tình của lập trình viên thành "tính năng mới được tài liệu hóa", phá hủy hoàn toàn các quy tắc kiến trúc ban đầu.
- **Cơ chế:** Không có lệnh auto-remap trong Kernel CLI. Mọi độ lệch trong `DRIFT.md` đều chặn lệnh `verify` cho đến khi có phán quyết chính thức.
- **Miễn trừ:** `forge drift waive --reason TEXT --until <sha|date>` cho phép tạm hoãn có thời hạn, tuyệt đối không vĩnh viễn.

---

### VII. Quy tắc Claim-Touch: Sửa code phải giải trình tài liệu bị chạm
- **Quy tắc:** Mọi thay đổi mã nguồn có git diff giao cắt với neo của bất kỳ Claim nào trong hệ thống BẮT BUỘC phải giải trình đầy đủ claim đó trong file `impact.md` dưới một trong ba trạng thái: `Unaffected` (kèm lý do), `Updated` (sửa lại nội dung claim), hoặc `Superseded` (thay thế bằng ADR mới).
- **Lý do:** Biến câu hỏi *"Tài liệu nào cần cập nhật khi code đổi?"* từ một sự phán đoán chủ quan thành một phép toán tập hợp cơ học không thể chối cãi.
- **Cơ chế:** Cổng kiểm soát `forge gate impact:post` tính toán tập giao và chặn đứng tiến trình nếu thiếu giải trình.
- **Miễn trừ:** Không có.

---

### VIII. Một nguồn chân lý duy nhất cho mỗi sự việc (Single truth source)
- **Quy tắc:** Mọi Claim chỉ có đúng một nguồn chân lý (`truth-source`): `code`, `tests`, `config`, `decision` (ADR), hoặc `spec`. Không bao giờ duy trì hai nguồn chân lý song song cho cùng một hành vi.
- **Lý do:** Tránh các cuộc tranh cãi vô tận khi xảy ra xung đột giữa code và tài liệu. Nguồn chân lý xác định rõ bên nào phải nhường bên nào.
- **Cơ chế:** Kiểm tra tính hợp lệ của trường `truth-source` trong `forge check`.
- **Miễn trừ:** Không có.

---

### IX. Không tuyên bố hoàn thành nếu thiếu bằng chứng tươi mới (Evidence before claims)
- **Quy tắc:** AI Coding Agent TUYỆT ĐỐI KHÔNG ĐƯỢC tuyên bố một task hoặc một change đã hoàn thành nếu chưa chạy lệnh kiểm chứng và thu được kết quả thành công ngay trong phiên làm việc hiện tại. Báo cáo nghiệm thu không tự viết tay mà phải được sinh tự động bởi máy (`verification.json`).
- **Lý do:** Ngăn chặn triệt để hành vi "báo cáo ảo" của AI — tự nhận đã làm xong và tất cả bài test đều pass trong khi thực tế chưa từng chạy lệnh test.
- **Cơ chế:** Lệnh `forge verify --change <N>` chạy test suite thực tế và đối soát 8 điều kiện trước khi sinh file `verification.json`.
- **Miễn trừ:** Cờ `--no-run` trong `verify` cho phép ghi nhận trạng thái chưa kiểm chứng (`unproven`) đối với các môi trường không có sẵn runtime test.

---

### X. Ngân sách ngữ cảnh là giới hạn cứng (Context budgets are hard ceilings)
- **Quy tắc:** Tập hợp tài liệu nạp liên tục vào mỗi phiên làm việc (`OVERVIEW.md` + chỉ mục claim + đầu ra `forge status`) BẮT BUỘC không được vượt quá **400 dòng văn bản**. Khi vượt quá ngân sách, phải tiến hành tỉa bớt hoặc di dời sang cơ chế nạp theo nhu cầu, tuyệt đối KHÔNG ĐƯỢC nâng trần ngân sách.
- **Lý do:** Nạp tài liệu quá dài sẽ gây loãng ngữ cảnh (context rot), khiến AI bị giảm sút khả năng suy luận logic và tốn kém token vô ích.
- **Cơ chế:** Lệnh `forge check` kiểm tra số dòng của tập nạp liên tục và báo lỗi nếu vượt quá 400 dòng.
- **Miễn trừ:** Không có.

---

### XI. Thích ứng quy mô linh hoạt, không hạ chuẩn kỷ luật (Scale down, never to zero)
- **Quy tắc:** Công việc đơn giản sẽ đi theo Track nhẹ hơn (Track A, Track B) để giảm bớt số lượng artifact, nhưng các cổng kiểm soát cốt lõi (G1, G5, verify) không bao giờ bị triệt tiêu.
- **Lý do:** Mọi sai sót lớn đều bắt nguồn từ tâm lý chủ quan coi thường những thay đổi "nhỏ".
- **Cơ chế:** Bộ định tuyến Track trong skill `forge` và cơ chế bánh cóc một chiều (One-way ratchet).
- **Miễn trừ:** Không có.

---

### XII. Con người kiểm soát qua các cổng tối thiểu nhưng quyết định (Decisive human gates)
- **Quy tắc:** Con người không can thiệp vào các bước vụn vặt giữa các task, nhưng nắm quyền tối cao tại các chốt chặn chiến lược: phê duyệt ý định/Track (G1), phê duyệt đặc tả (G2), phê duyệt kiến trúc (G3), phê duyệt cập nhật tri thức vĩnh viễn (G5), và các điểm dừng khẩn cấp về bảo mật/dữ liệu (G4, G6).
- **Lý do:** Đảm bảo sản phẩm đi đúng định hướng của con người trong khi vẫn giải phóng tối đa năng suất tự động của AI.
- **Cơ chế:** Các cổng G1, G4, G6 là vô điều kiện. Cổng G2, G3, G5 có thể cấu hình linh hoạt trong `autonomy`.
- **Miễn trừ:** Không có cho G1, G4, G6.

---

### XIII. Git là Cơ sở dữ liệu duy nhất, Văn bản thuần là Trạng thái (Git is the database)
- **Quy tắc:** Toàn bộ tri thức, đặc tả, kế hoạch và cấu hình BẮT BUỘC phải là các file văn bản thuần (Markdown, YAML, JSON) lưu trữ trực tiếp trong Git. Tuyệt đối không dùng database nhị phân, không daemon chạy ngầm.
- **Lý do:** Giúp mọi thay đổi tri thức đều có thể diff, merge, review qua Pull Request và truy vết lịch sử bằng `git blame` / `git log` như code.
- **Cơ chế:** Toàn bộ Kernel CLI chỉ đọc và ghi file văn bản trên filesystem của Git repository.
- **Miễn trừ:** Không có.

---

### XIV. Truy vết Hai chiều Tường minh (Bidirectional traceability)
- **Quy tắc:** Mọi Requirement phải liên kết với Task triển khai và bài Test tương ứng. Mọi Claim phải truy vết ngược được về vị trí code mà nó chi phối và quyết định kiến trúc (ADR) đã sinh ra nó.
- **Lý do:** Khi muốn sửa đổi một quy tắc, kỹ sư có thể biết ngay nó tác động đến những phần code nào; ngược lại khi đọc một đoạn code, kỹ sư biết ngay nó phục vụ yêu cầu nghiệp vụ nào.
- **Cơ chế:** Chỉ mục `derived/trace.json` được tái tạo tự động và kiểm tra qua lệnh `forge trace`.
- **Miễn trừ:** Không có.

---

### XV. Bất cứ điều gì tính toán được đều phải là Mã thoát lệnh (Exit code enforcement)
- **Quy tắc:** Một quy định chỉ có giá trị thực thi khi nó được bảo vệ bởi một bài kiểm tra có thể trả về Exit Code (0 hoặc khác 0). Không đưa ra quy định suông bằng văn bản nếu không có công cụ kiểm tra vi phạm.
- **Lý do:** Lời khuyên bằng văn xuôi sẽ bị lãng quên; chỉ có mã thoát lệnh tại các cổng kiểm soát mới có thể ngăn chặn code lỗi được đưa vào hệ thống.
- **Cơ chế:** `forge gate` và `forge check` định nghĩa chuẩn hóa các mã thoát lệnh cho toàn bộ quy trình.
- **Miễn trừ:** Không có.

---

### XVI. Kỷ luật TDD nghiêm ngặt theo từng đơn vị công việc (Strict TDD per task)
- **Quy tắc:** Khi triển khai code trong giai đoạn `implement`, AI bắt buộc phải viết bài test trước (chứng kiến test FAIL), sau đó mới viết mã nguồn để test PASS, và cuối cùng refactor.
- **Lý do:** Viết test sau khi đã code xong thường dẫn đến việc viết các bài test hời hợt, chỉ để cho có, không thực sự kiểm tra được các trường hợp biên nguy hiểm.
- **Cơ chế:** Quy trình trong skill `implement` và việc đối soát test coverage tại cổng `verify`.
- **Miễn trừ:** Chỉ áp dụng cho code có thể kiểm thử tự động. Những phần giao diện người dùng thuần túy không có logic nghiệp vụ có thể được kiểm chứng bằng kịch bản thủ công được ghi nhận.
