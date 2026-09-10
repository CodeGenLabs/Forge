# CONSTITUTION.md — forge

**Trạng thái:** bản dự thảo chờ phê chuẩn. Phiên bản 0.1.0. Chưa phê chuẩn.

Đây là tài liệu chi phối tối cao của harness. Nó ràng buộc hai phương diện:

- **quá trình phát triển của chính harness** — những gì chúng ta được phép xây dựng và những gì không;
- **hành vi của harness** — những gì nó yêu cầu đối với bất kỳ dự án nào áp dụng nó.

Nếu một nguyên tắc chỉ áp dụng cho một trong hai phương diện trên, tài liệu sẽ nêu rõ.

## Tài liệu này khác biệt như thế nào so với các bản hiến chương trong tài liệu tham chiếu

File `constitution-template.md` của Spec Kit chỉ là một danh sách các nguyên tắc kèm phần chân trang quản trị (governance footer), và lệnh `/analyze` của nó coi các vi phạm mặc định là CRITICAL — nhưng không có cơ chế nào tính toán xem một nguyên tắc có thực sự bị vi phạm hay không. Một nguyên tắc mà vi phạm của nó không thể bị phát hiện thì chỉ là một sở thích/nguyện vọng (preference).

Vì vậy, mỗi nguyên tắc ở đây đều mang 4 trường thông tin:

| Trường | Ý nghĩa |
|---|---|
| **Quy tắc (Rule)** | Tuyên bố mang tính quy chuẩn: BẮT BUỘC (MUST) / KHÔNG ĐƯỢC (MUST NOT) / NÊN (SHOULD) |
| **Lý do (Why)** | Bằng chứng hoặc lập luận logic. Được trích dẫn nguồn cụ thể từ các nghiên cứu |
| **Cơ chế (Mechanism)** | Yếu tố nào phát hiện vi phạm: một kernel check, một cổng (gate), quy trình review, hoặc `không có (định hướng - aspirational)` |
| **Miễn trừ (Waiver)** | Cách thức để bỏ qua/miễn trừ nguyên tắc đó, và chi phí phải đánh đổi là gì |

Một nguyên tắc có `Cơ chế: không có` sẽ được dán nhãn rõ ràng là định hướng (aspirational). Thành thật về những nguyên tắc nào thực sự được thực thi sẽ hữu ích hơn nhiều so với việc giả vờ rằng tất cả chúng đều đang được áp dụng.

---

## I. Xác định trước, xác suất sau (Deterministic before probabilistic)

**Quy tắc.** Bất kỳ kiểm tra nào *có thể* viết thành một script xác định (deterministic script) thì BẮT BUỘC phải là script. Một mô hình ngôn ngữ KHÔNG ĐƯỢC PHÉP là thẩm quyền duy nhất cho bất kỳ cổng kiểm soát (gate) nào. Việc chuyển một kiểm tra từ sự phán đoán của LLM sang một script — bằng cách bổ sung quy ước ID, một trường dữ liệu, hoặc một anchor — luôn luôn là một cải tiến và BẮT BUỘC phải được ưu tiên hơn việc cải thiện prompt.

**Lý do.** Việc thực thi chỉ dựa trên prompt buộc phải leo thang lên mức cưỡng chế để giữ kỷ luật (`<EXTREMELY-IMPORTANT>` của Superpowers), và ngay cả khi đó nó vẫn có thể bị "thương lượng". Lệnh `/analyze` của Spec Kit yêu cầu mô hình xây dựng danh mục ID bằng suy luận từ khóa rồi tính toán tỷ lệ phần trăm bao phủ "xác định" — một tác vụ mà một lệnh grep 5 dòng có thể làm hoàn hảo. Trình linter của chính BMAD đã chỉ rõ ranh giới này: "LLM đếm sai ID và bỏ sót các placeholder nguyên văn; grep thì không."

**Cơ chế.** Mã thoát (exit code) của `forge gate` là thẩm quyền chặn (blocking authority) duy nhất. Một skill muốn chặn tiến trình phải viện dẫn một kernel check. Được review ở mỗi lần thay đổi skill.

**Miễn trừ.** Không có. Đây là nguyên tắc nền tảng mà các nguyên tắc còn lại dựa vào.

---

## II. Tìm hiểu trước khi sửa; tái hiện trước khi sửa lỗi (Investigate before modifying; reproduce before fixing)

**Quy tắc.** Không thực hiện hành động triển khai code nào trước khi hành vi hiện tại có liên quan được đọc và nêu rõ. Không sửa bug trước khi có một test tái hiện bug được commit và ở trạng thái thất bại (failing test). Tìm nguyên nhân gốc rễ trước khi đưa ra biện pháp khắc phục — việc chỉ sửa triệu chứng bên ngoài là một thất bại, không phải là thành công một phần.

**Lý do.** Sự hội tụ độc lập: `systematic-debugging` của Superpowers ("TUYỆT ĐỐI KHÔNG SỬA LỖI NẾU CHƯA ĐIỀU TRA NGUYÊN NHÂN GỐC RỄ") và quy trình mặc định của mini-SWE-agent ("Tạo script tái hiện vấn đề" trước khi "Chỉnh sửa mã nguồn") đều đi đến cùng một quy tắc từ hai hướng tiếp cận trái ngược nhau — một thư viện phương pháp luận và một vòng lặp tối ưu hóa theo benchmark. Đó là tín hiệu phương pháp luận mạnh mẽ nhất trong toàn bộ tài liệu tham chiếu.

**Cơ chế.** Đồ thị DAG của `bugfix` yêu cầu artifact `reproduce` trước khi đến `tasks`. Cổng kiểm soát tại `implement:pre`. Đối với tính năng (features), `investigate` phải đứng trước `spec` trong DAG.

**Miễn trừ.** Các thăm dò thuộc Track A có thể bỏ qua độ sâu điều tra, chứ không bỏ qua bước điều tra. Một bugfix không được phép miễn trừ `reproduce`; nếu bug không thể tái hiện được, dữ kiện đó chính là kết luận tìm thấy và thay đổi sẽ dừng lại ở đó.

---

## III. Đặc tả trước khi triển khai, kích thước tương xứng với thay đổi (Specification before implementation, sized to the change)

**Quy tắc.** Mọi thay đổi làm biến đổi hành vi quan sát được (observable behaviour) BẮT BUỘC phải mang theo một bản chênh lệch đặc tả (spec delta) với ít nhất một kịch bản kiểm thử được cho mỗi yêu cầu. Thay đổi nào không làm thay đổi hành vi BẮT BUỘC phải khai báo `skip_spec: true` kèm lý do. Yếu tố co giãn theo quy mô thay đổi là *artifact*, tuyệt đối không phải là *sự phê duyệt (approval)*.

**Lý do.** OpenSpec từ chối các thay đổi không có spec delta trừ khi sự bỏ qua đó được khai báo tường minh và được ghi nhận — đây là khuôn mẫu đúng đắn, vì nó làm cho ngoại lệ trở nên minh bạch thay vì rơi vào tình trạng không được thực thi hoặc không thể miễn trừ. Lời chỉ trích "phát triển dựa trên spec quá nặng nề" là đúng với một dòng sửa đổi đơn giản nhưng lại sai hoàn toàn với một hệ thống con, đó là lý do tại sao bộ định tuyến (router spike/bounded/architectural của Superpowers) tồn tại.

**Cơ chế.** Cổng `spec:post`: ngữ pháp chuẩn, ≥1 kịch bản cho mỗi yêu cầu, không còn `[NEEDS CLARIFICATION]`, từ chối các thay đổi zero-delta trừ khi có `skip_spec` kèm lý do.

**Miễn trừ.** `skip_spec: true` + lý do, được ghi nhận trong `changes/NNNN/.forge.yaml`. Việc tự bịa ra một yêu cầu chỉ để làm vừa lòng validator là hành vi vi phạm nguyên tắc này, chứ không phải tuân thủ nó.

---

## IV. Lưu trữ các phán đoán; phái sinh các dữ kiện (Store judgements; derive facts)

**Quy tắc.** Một dữ kiện KHÔNG ĐƯỢC lưu trữ trong tri thức hệ thống nếu một kỹ sư có năng lực có thể trích xuất lại nó từ mã nguồn tuân thủ tiêu chuẩn. Bố cục thư mục, phiên bản công nghệ (stack versions), danh sách export, đồ thị phụ thuộc và danh mục test đều là phái sinh (derived), tuyệt đối không tự viết thủ công. Những gì được lưu trữ là những gì code không thể tự nói lên: trách nhiệm, ý định, ràng buộc, từ vựng, điều cấm và lý do.

**Lý do.** Tiêu chí kết nạp của BMAD nêu nguyên văn: *"những quyết định mà người xây dựng trong tương lai không thể đọc ra từ code chuẩn mực."* Mọi dự án trong tài liệu tham chiếu lưu trữ dữ kiện tĩnh (`STACK.md`, `STRUCTURE.md` của GSD; `research.md` theo từng tính năng của Spec Kit) đều mục rữa ở chính những tệp đó đầu tiên, bởi vì dữ kiện chính là thứ mà commit tiếp theo có thể mâu thuẫn ngay lập tức.

**Cơ chế.** Các linter chống nhiễu của `forge check`: phát hiện mùi claim có thể phái sinh (derivable-claim smell), mùi liệt kê thư mục (directory-listing smell), mùi dữ kiện công nghệ (stack-fact smell) (SYSTEM_KNOWLEDGE.md §7.3). Đưa ra cảnh báo kèm lộ trình xác nhận rõ ràng, cộng với review tại G5.

**Miễn trừ.** Đặt `# forge:not-derivable <reason>` trên claim, việc này được ghi nhận và có thể review.

---

## V. Mọi claim đều được neo, gắn nhãn và có bằng chứng (Every claim is anchored, labelled, and evidenced)

**Quy tắc.** Mọi claim được lưu trữ BẮT BUỘC phải có một ID ổn định, một `truth-source` (nguồn chân lý), và ít nhất một neo (anchor) trỏ vào code — ngoại trừ các claim loại `constraint` (bắt nguồn từ bên ngoài repository) và `concept` (không có một vị trí duy nhất trong code). Một claim được đánh dấu `enforced` BẮT BUỘC phải nêu tên một artifact sẽ thất bại về mặt cơ học khi claim bị vi phạm, và artifact đó BẮT BUỘC phải tồn tại và chạy pass.

**Lý do.** Một claim không có neo sẽ không bao giờ có thể kiểm tra được và sẽ mục rữa trong âm thầm; nó chỉ là một dòng comment trong một tệp mà không ai diff tới. Các neo mang lại khả năng phát hiện lỗi thời mang tính xác định, không phụ thuộc vào định dạng định dạng (cơ chế của Fiberplane). Nhãn nguồn chân lý biến việc xử lý mâu thuẫn thành một thao tác tra cứu thay vì một cuộc tranh luận vô tận. Bằng chứng có tên cụ thể là thứ phân tách giữa "chúng tôi tin vào điều này" và "điều này không thể hỏng nếu không có thứ gì đó báo đỏ".

**Cơ chế.** `forge check --scope store`: sự hiện diện của anchor, tính hợp lệ của các trường, giải quyết bằng chứng, và logic `enforced` ⇒ evidence-passes. Chặn (blocking) tại `sync:pre` và trong pre-commit hook.

**Miễn trừ.** Một claim có thể ở trạng thái `asserted` (khẳng định) thay vì `enforced` (bắt buộc) — đó không phải là miễn trừ, mà là một trạng thái trung thực, và `forge status` sẽ báo cáo tỷ lệ này.

---

## VI. Không bao giờ âm thầm đối soát tài liệu theo code (Documentation is never silently reconciled to code)

**Quy tắc.** Harness KHÔNG ĐƯỢC chứa bất kỳ thao tác nào tự động viết lại tri thức hệ thống cho khớp với phần triển khai code. Độ lệch (drift) được phát hiện BẮT BUỘC phải được phân loại và BẮT BUỘC phải có một phán quyết được ghi nhận: code sai (V1), claim chưa bao giờ đúng (V2), quyết định đã thay đổi (V3, cần có ADR), hoặc claim chưa đủ cụ thể (V4). LLM có thể đề xuất phán quyết. Chỉ con người mới có quyền ghi nhận phán quyết.

**Lý do.** Đây là yêu cầu trọng tâm của đề bài và nó được hỗ trợ trực tiếp bởi các phép đo lường thực tế: LLM phát hiện lỗi tài liệu ở mức 67–94% nhưng giảm sút 21–43 điểm phần trăm khi chỉ có phần triển khai thay đổi (arXiv:2604.03447) — đúng trường hợp mà việc xử lý độ lệch phải đối mặt — và độ tự tin của chúng "hầu như không phân biệt được giữa phán đoán đúng và phán đoán sai". Hành vi `drift_action: auto-remap` của GSD là thứ mà nguyên tắc này sinh ra để nghiêm cấm: nó âm thầm viết lại bản đồ để code luôn luôn đúng, điều này hủy hoại hoàn toàn quyết định ban đầu.

**Cơ chế.** Không tồn tại lệnh nào như vậy trong kernel (ARCHITECTURE.md §2.2). Các mục trong `DRIFT.md` chặn lệnh `verify` cho đến khi chúng có phán quyết hoặc có miễn trừ có thời hạn. Cổng G6 vĩnh viễn là cổng thủ công.

**Miễn trừ.** `forge drift waive --reason --until`, được ghi nhận và có thời hạn hết hạn. Tuyệt đối không âm thầm, không bao giờ vĩnh viễn.

---

## VII. Thay đổi kiến trúc đòi hỏi lập luận tường minh (Architecture changes require explicit reasoning)

**Quy tắc.** Thay đổi một claim thuộc loại `architecture`, phá vỡ giao diện công khai (public interface), hoặc thay đổi một bất biến (invariant) BẮT BUỘC phải đi kèm với một bản ADR thay thế quyết định trước đó. Một ADR đã được chấp thuận KHÔNG ĐƯỢC sửa đổi nội dung; nó chỉ có thể bị thay thế (superseded). Một ADR BẮT BUỘC phải nêu tên ít nhất một claim mà nó chứng minh, và mọi claim kiến trúc BẮT BUỘC phải nêu tên ADR sinh ra nó.

**Lý do.** OpenSpec giữ lý do lập luận trong tệp `design.md` theo từng thay đổi, sau đó được lưu trữ lại (archive), vì vậy lý do một quyết định đang có hiệu lực tồn tại cuối cùng lại bị chôn vùi trong `changes/archive/2026-01-06-.../design.md`. Lý do lập luận (rationale) là thứ duy nhất không bao giờ có thể trích xuất lại từ mã nguồn, do đó nó là thứ duy nhất bắt buộc phải mang tính vĩnh viễn.

**Cơ chế.** Các mục `Superseded` trong `impact.md` yêu cầu phải có một ADR hiện hữu; các cổng `design:post` và `sync:pre` xác minh các liên kết hai chiều `since:` / `supersedes:`; lệnh `forge sync` từ chối sửa đổi claim nếu nó yêu cầu ADR mà không có.

**Miễn trừ.** Phán quyết V2 (claim chưa bao giờ đúng) cho phép đính chính claim mà không cần ADR, vì chưa có quyết định nào từng được đưa ra — chỉ là ghi nhận nhầm. Thay vào đó, nó yêu cầu một ghi chú bằng chứng được ghi lại.

---

## VIII. Test là bằng chứng, và bằng chứng phải tươi mới hoặc không có giá trị (Tests are evidence, and evidence is fresh or absent)

**Quy tắc.** Một khẳng định hoàn thành (completion claim) BẮT BUỘC phải đi kèm với đầu ra kiểm chứng (verification output) được tạo ra trong chính phiên chạy đó. Mọi yêu cầu BẮT BUỘC phải được giải tỏa bởi ít nhất một test pass có khai báo nó (`@covers`). Một bài test chưa từng được quan sát thấy fail thì không phải là bằng chứng. "Tests pass" chỉ là một trong tám điều kiện để hoàn thành, không phải là định nghĩa của hoàn thành.

**Lý do.** Superpowers cần hẳn một skill cho việc này ("KHÔNG CÓ KHẲNG ĐỊNH HOÀN THÀNH NẾU THIẾU BẰNG CHỨNG KIỂM CHỨNG TƯƠI MỚI"), điều này cho thấy xu hướng đi chệch hướng mạnh mẽ đến mức nào. Mẫu tác vụ của Spec Kit biến test thành TÙY CHỌN trong khi mẫu spec của nó lại đòi hỏi các test độc lập cho mỗi user story — chuỗi truy vết bị đứt gãy chính tại điểm đó. GSD cần cơ chế `broken-windows` để ngăn chặn việc tuyên bố `done` trên một đống code stub và các test bị skip.

**Cơ chế.** Lệnh `verify` tạo ra `verification.json` từ đầu ra lệnh vừa chạy tươi mới; các cổng `requirement_cover` và `claim_evidence`; bước chuyển đổi từ đỏ sang xanh được ghi lại trong quỹ đạo (trajectory) của từng task; các mục mở trong `DEBT.md` chặn trạng thái `done`.

**Miễn trừ.** Các điều kiện trong `DEBT.md` và `DRIFT.md` có thể được miễn trừ kèm lý do và thời hạn. Build, typecheck, lint, tests, độ bao phủ yêu cầu và độ tươi mới của phái sinh thì KHÔNG ĐƯỢC miễn trừ.

---

## IX. Tri thức chỉ bị xóa bỏ khi có căn cứ rõ ràng (Knowledge is deleted only on named grounds)

**Quy tắc.** Một claim chỉ có thể bị hủy bỏ (retired) hoặc xóa dựa trên một trong bốn căn cứ: (1) lỗi thời hoặc sai lệch, kèm bằng chứng cụ thể; (2) được thực thi bằng cơ học bởi một kiểm tra phát hiện chính xác vi phạm mà nó nêu tên; (3) có hại hoặc mâu thuẫn, bị thua trong quá trình đối soát với một claim đang hiệu lực; (4) con người đã phê duyệt việc xóa bỏ cụ thể này, được hỏi dưới dạng một mục riêng biệt. Tính ngắn gọn súc tích không phải là căn cứ. Dạo gần đây không thấy cái gì bị fail không phải là căn cứ. "Agent có thể tự suy ra được" không phải là căn cứ. **"Nó có thể tự khám phá được ở đâu đó trong repository" TUYỆT ĐỐI KHÔNG BAO GIỜ tự thân nó là căn cứ.**

**Lý do.** Được tiếp thu từ `project-context` của BMAD, vốn là chính sách được lập luận cẩn trọng nhất trong tài liệu tham chiếu, và lý do của chính nó là mấu chốt: kiểu lý luận cuối cùng "là thứ lý luận làm rỗng những tệp tài liệu tốt". Sự phình to là thất bại hiển nhiên; nhưng một con agent thích dọn dẹp làm biến mất những tri thức quý báu được tích lũy lại là thất bại tinh vi và tồi tệ hơn, bởi vì một quy tắc đang hoạt động tốt sẽ tự xóa sạch bằng chứng về sự cần thiết của chính nó.

**Cơ chế.** `forge retire <ID> --ground N --evidence TEXT` ghi nhận căn cứ; căn cứ số 4 yêu cầu con người duyệt; `forge check` từ chối lệnh retire nếu không có căn cứ. Các claim đã retire vẫn nằm lại trong tệp, nhưng bị loại khỏi các phép kiểm tra và ngân sách dòng.

**Miễn trừ.** Không có. Bản thân các căn cứ nêu trên *chính là* cơ chế miễn trừ.

---

## X. Mỗi dòng ngữ cảnh nạp-liên-tục đều phải trả giá trong mọi phiên làm việc (Every line of always-loaded context is paid for in every session)

**Quy tắc.** Tập hợp nạp-liên-tục (always-loaded set gồm `OVERVIEW.md` cộng với các tệp claim bắt buộc) BẮT BUỘC phải nằm trong ngân sách dòng của nó. Vượt quá ngân sách phải được giải quyết bằng cách cắt giảm bớt claim hoặc chuyển nó ra sau một điều kiện kích hoạt có thể quan sát được (observable trigger). **Ngân sách tuyệt đối không bao giờ được tự ý tăng lên.** Một con trỏ dẫn ra ngoài tập nạp-liên-tục BẮT BUỘC phải nêu một trigger mà agent có thể quan sát được — một đường dẫn, một loại tệp, một phase có tên — tuyệt đối không dùng trigger mà agent phải tự phán đoán ("khi tác vụ phức tạp") hoặc tự theo dõi về chính nó ("trước lần chỉnh sửa đầu tiên của bạn").

**Lý do.** Nghiên cứu về mục rữa ngữ cảnh (context-rot) của Chroma cho thấy sự suy giảm hiệu quả ở mỗi nấc tăng độ dài đầu vào trên 18 mô hình tiên tiến nhất, từ rất lâu trước khi chạm đến giới hạn cửa sổ ngữ cảnh. BMAD cũng độc lập đi đến cùng một kết luận: "Mỗi dòng đều phải trả giá trong mọi phiên làm việc, và khả năng tuân thủ chỉ dẫn suy giảm khi tập nạp mở rộng." Và: "Một chỉ mục mà agent phải tự chọn để fetch sẽ bị bỏ qua; một chỉ mục đã nằm sẵn trong ngữ cảnh thì không."

**Cơ chế.** Kiểm tra ngân sách của `forge check`, mang tính chặn (blocking). Giá trị `budgets.always_loaded_lines` trong config; việc nâng giới hạn này đòi hỏi phải sửa đổi tài liệu hiến chương này.

**Miễn trừ.** Không có. Sửa đổi ngân sách là một lần sửa đổi hiến chương (§Quản trị), đó chính là lực ma sát kiểm soát mà chúng ta mong muốn.

---

## XI. Càng ít cổng kiểm soát càng tốt, và mỗi cổng phải chứng minh được giá trị (Few gates, and each one earns its place)

**Quy tắc.** Các cổng do con người duyệt được liệt kê cụ thể, ngắn gọn, và mỗi cổng được biện minh trong một câu duy nhất: ý định & track, spec, thiết kế & ADR, thao tác rủi ro cao, biến động tri thức, phán quyết độ lệch. Harness KHÔNG ĐƯỢC hỏi con người bất cứ điều gì mà việc quét repository có thể trả lời được. Yêu cầu con người xác nhận một sự thật đã được kiểm tra qua đường dẫn là một khiếm khuyết, không phải sự cẩn trọng. Trong một kế hoạch đang thực thi, những điểm mơ hồ phải được quyết định và ghi nhận lại, chứ không được xếp hàng chờ hỏi.

**Lý do.** Superpowers rất đúng khi cho rằng một kế hoạch đang chạy không nên bị dừng lại chờ con người ("Phán quyết, không đình trệ"), và cũng đúng khi cho rằng một số cổng là vô điều kiện. Sự tổng hợp ở đây là *ít* cổng thay vì *không có* hoặc *quá nhiều*. Quy tắc của BMAD là lưỡi dao sắc bén: "Không bao giờ hỏi những gì một lệnh quét có thể trả lời." Một harness liên tục hỏi sẽ khiến con người click bừa cho qua, điều này không khác gì việc không có cổng kiểm soát nào.

**Cơ chế.** Danh sách cổng trong WORKFLOW.md §4 là danh sách đóng. Việc thêm cổng là một lần sửa đổi hiến chương. Cấu hình `autonomy` chỉ có thể nới lỏng G3 và G5; G1, G2, G4 và G6 vĩnh viễn là thủ công.

**Miễn trừ.** Nới lỏng `autonomy` theo từng dự án cho G3/G5, được ghi nhận trong config kèm lý do.

---

## XII. Giới hạn phiên chạy, lưu vết quỹ đạo liên tục (Bounded runs, persisted trajectories)

**Quy tắc.** Mọi giai đoạn (phase) và mọi tác vụ (task) đều chạy dưới các giới hạn được thực thi bằng mã nguồn: số bước, thời gian thực (wall-clock), chi phí, số lần thất bại liên tiếp. Vượt quá giới hạn sẽ chấm dứt phiên chạy kèm lý do được ghi lại. Quỹ đạo (trajectory) được ghi vào đĩa ở mỗi bước, không phải đợi đến khi kết thúc.

**Lý do.** mini-SWE-agent thực thi chính xác điều này chỉ trong ~200 dòng code và đó là cơ chế đảm bảo độ tin cậy ít tốn kém nhất trong tài liệu tham chiếu. Nó biến việc "agent chạy lung tung mất kiểm soát trong 2 tiếng" từ một vấn đề giám sát con người thành một thất bại có giới hạn kèm log rõ ràng.

**Cơ chế.** `budgets.phase` trong config; skill điều phối sẽ truyền các giới hạn cho từng subagent; các file trajectory theo từng task lưu tại `changes/NNNN/trajectories/`.

**Miễn trừ.** Ghi đè theo từng lần gọi lệnh với một cờ (flag) tường minh, được ghi nhận trong trajectory.

---

## XIII. Không chỉnh sửa lan man ngoài phạm vi (No unrelated modifications)

**Quy tắc.** Một thay đổi chỉ được phép chạm vào những gì mà các task của nó khai báo. Những bản sửa lỗi tiện tay (opportunistic fixes), định dạng lại code bừa bãi, và các đợt tái cấu trúc không liên quan KHÔNG ĐƯỢC PHÉP đi kèm. Một khiếm khuyết được nhận thấy khi đang làm việc sẽ được đưa vào `DEBT.md` hoặc trở thành một change riêng biệt.

**Lý do.** Các chỉnh sửa không liên quan phá hủy khả năng review — vốn là sự kiểm soát thực tế duy nhất đối với đầu ra của agent — và chúng làm ô nhiễm tập hợp claim-touch: một tệp không liên quan trong git diff sẽ kéo các claim không liên quan vào việc giải trình và tập cho mọi người thói quen viết "unaffected" (không ảnh hưởng) mà không cần suy nghĩ.

**Cơ chế.** Cổng `implement:task:post`: git diff chỉ chạm vào các tệp được task khai báo. Chặn (blocking).

**Miễn trừ.** Sửa đổi task để bổ sung tệp, việc này hoàn toàn miễn phí và chỉ tốn một dòng. Đó chính là lộ trình được chủ đích thiết kế.

---

## XIV. Không trừu tượng hóa thừa thãi; harness có ngân sách kích thước (No unnecessary abstraction; the harness has a size budget)

**Quy tắc.** Harness BẮT BUỘC phải nằm trong ngân sách tăng trưởng tại ARCHITECTURE.md §8: 9 skills (trần tối đa 12), ~20 lệnh kernel (trần 25), 12 cổng (trần 16), 5 lược đồ workflow (trần 7), ~3.000 dòng code kernel, tối đa 250 dòng cho mỗi skill. Khi chạm mức trần, một thứ gì đó phải được gộp hoặc xóa trước khi thêm thứ mới. Một cổng chưa từng kích hoạt lần nào sẽ bị xóa trong đợt review tiếp theo.

**Lý do.** Bài học thực nghiệm rõ ràng nhất trong tài liệu tham chiếu: các framework này tăng trưởng nhanh hơn các dự án mà chúng phục vụ. GSD đã đạt tới 44 năng lực, ~90 workflow và 4 cách biểu diễn cùng tồn tại cho cùng một hệ thống. BMAD đạt 29 skills và 2.4 MB với 5 nhân cách (personas) cùng một builder để tạo thêm. Ban đầu không dự án nào như vậy. Những con số cụ thể trong một tài liệu đòi hỏi quy trình sửa đổi hiến chương mới thay đổi được chính là hàng rào phòng thủ duy nhất từng phát huy tác dụng.

**Cơ chế.** `forge status` báo cáo từng ngân sách. Một checklist phát hành sẽ xác minh chúng. `Cơ chế: review` đối với số dòng code (LOC) và độ dài skill.

**Miễn trừ.** Sửa đổi hiến chương kèm lý do được ghi nhận. Không phải là một phán đoán tùy hứng nhất thời.

---

## XV. Ưu tiên kiểm tra tự động hơn một quy tắc bằng văn xuôi (Prefer a check over a prose rule)

**Quy tắc.** Trước khi viết một quy tắc dưới dạng văn xuôi — trong tài liệu này, trong một claim, hay trong một skill — hãy tự hỏi liệu một hook, linter, formatter, kiểu dữ liệu (type) hay bài kiểm tra CI có thực thi nó tốt hơn không. Nếu có, hãy xây dựng bài kiểm tra đó; văn xuôi chỉ là phương án dự phòng nếu việc kiểm tra tự động bị từ chối. Một quy tắc văn xuôi sau này được một bài kiểm tra tự động thực thi sẽ bị loại bỏ theo căn cứ 2.

**Lý do.** Quy tắc của BMAD, và là cơ chế đứng sau Nguyên tắc I. Đây cũng là con đường thực tế giúp kho lưu trữ thu nhỏ lại theo thời gian thay vì phình to: tri thức đã được cơ giới hóa thì không cần phải ghi nhớ nữa.

**Cơ chế.** Review tại G5 và ở mỗi lần thay đổi skill. `Cơ chế: review` — trung thực là mang tính định hướng, và được dán nhãn như vậy.

**Miễn trừ.** Không áp dụng.

---

## XVI. Báo cáo trung thực (Report faithfully)

**Quy tắc.** Nêu rõ những gì đã chạy và những gì nó trả về. Nếu một kiểm tra bị bỏ qua, hãy nói rõ. Nếu một bước được miễn trừ, hãy nêu rõ căn cứ miễn trừ. Không mô tả hành vi dự kiến như thể đó là hành vi đã quan sát được, không báo cáo một phiên chạy dở dang là đã hoàn thành, và không xoa dịu một phán quyết thất bại. Một kết quả `verdict: pass` có đi kèm miễn trừ phải được báo cáo là `pass (1 waiver)`, tuyệt đối không được báo cáo là `pass`.

**Lý do.** Mọi nguyên tắc khác ở đây đều phụ thuộc vào tính trung thực của các báo cáo. Một agent báo cáo một cách lạc quan tếu sẽ biến một harness đầy cổng kiểm soát thành một vở kịch trình diễn, và thất bại trở nên vô hình chính vì mọi thứ nhìn qua đều mang màu xanh.

**Cơ chế.** `verification.json` được tạo ra từ đầu ra lệnh được capture trực tiếp, không bao giờ được viết thủ công; các miễn trừ xuất hiện trong đó và trong `forge status`. Ngoài ra: review của con người.

**Miễn trừ.** Không có.

---

## Quản trị (Governance)

**Thứ tự ưu tiên.** Tài liệu này có hiệu lực cao hơn các skills, templates và cấu hình theo từng dự án. Khi một giá trị trong `.forge/config.yaml` xung đột với một nguyên tắc, nguyên tắc sẽ thắng và `forge check` sẽ báo cáo cấu hình đó là không hợp lệ. Khi một claim xung đột với một nguyên tắc, nguyên tắc sẽ thắng và claim đó là một điểm phát hiện sai phạm (finding).

**Thứ tự ưu tiên trong một dự án.** Đối với các câu hỏi về *hệ thống đang được xây dựng*, tài liệu này không cạnh tranh với kho lưu trữ claim: thẩm quyền thuộc về từng dữ kiện riêng biệt (SYSTEM_KNOWLEDGE.md §3.1). Tài liệu này chi phối *cách thức công việc được thực hiện*, không chi phối *những gì là đúng về hệ thống*.

**Sửa đổi hiến chương (Amendment).** Một lần sửa đổi hiến chương là một thay đổi thuộc loại `knowledge-only` mang theo: git diff, lý do, bằng chứng, và một **báo cáo tác động đồng bộ (sync impact report)** nêu tên mọi skill, template, gate, schema và budget đã được kiểm tra lại để đảm bảo tính đồng bộ — kèm kết quả kiểm tra cho từng mục. (Tiếp thu khối `SYNC IMPACT REPORT` của Spec Kit.) Quy chuẩn phiên bản ngữ nghĩa (SemVer): MAJOR khi xóa bỏ hoặc đảo ngược một nguyên tắc, MINOR khi thêm một nguyên tắc hoặc mở rộng đáng kể một nguyên tắc, PATCH khi làm rõ câu chữ mà không thay đổi nghĩa vụ.

**Phê chuẩn (Ratification).** Phiên bản 0.1.0 là bản dự thảo. Nó được phê chuẩn khi bản MVP trong [MVP.md](MVP.md) thành hình và trường `Cơ chế` của mọi nguyên tắc đã được đối chiếu với mã nguồn thực tế — bao gồm cả những nguyên tắc hóa ra là `không có (định hướng)`, khi đó chúng phải được cơ giới hóa hoặc được chấp nhận tường minh là mang tính định hướng.

**Chu kỳ xem xét (Review cadence).** Cứ sau mỗi 10 thay đổi, hoặc khi có bất kỳ sửa đổi hiến chương nào: các ngân sách có được giữ vững không? có cổng nào chưa từng kích hoạt không? có nguyên tắc định hướng nào đã có thể cơ giới hóa chưa? có claim nào trong kho đã được thực thi bằng cơ học và do đó có thể hủy bỏ theo căn cứ 2 không?

**Tự áp dụng (Self-application).** Harness được phát triển dưới các quy tắc của chính nó ngay từ thay đổi đầu tiên sau khi MVP hoàn thành. Bất cứ điều gì quá phiền hà khó chịu khi áp dụng cho chính repository này cũng sẽ quá phiền hà khó chịu khi áp dụng cho một repository thực tế, và sự khó chịu đó chính là tín hiệu phản hồi hữu ích nhất có thể có.

**Phiên bản**: 0.1.0 · **Phê chuẩn**: — (dự thảo) · **Sửa đổi lần cuối**: 2026-09-10
