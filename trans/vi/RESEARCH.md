# RESEARCH.md — Nghiên cứu về Harness kỹ nghệ phần mềm cá nhân

**Trạng thái:** đầu ra của giai đoạn nghiên cứu. Chưa có mã nguồn triển khai.
**Ngày nghiên cứu:** 2026-09-10.
**Phương pháp:** tất cả 6 repository được nêu tên (cộng với 1 repository kế nhiệm) đều được shallow-clone và đọc trực tiếp từ mã nguồn, không đọc qua tài liệu quảng bá. Ở những nơi hành vi không thể xác định từ văn xuôi, các script thực tế, schema, linter và các module TypeScript/Python đã được đọc chi tiết. Các khẳng định từ bên ngoài được trích dẫn từ các nguồn sơ cấp (các bài báo khoa học, repo công cụ, tài liệu nhà phát triển). Các bản tóm tắt từ công cụ tìm kiếm chỉ được sử dụng để *tìm ra* các nguồn sơ cấp.

**Quy ước đọc được sử dụng xuyên suốt tài liệu này**

| Ký hiệu | Ý nghĩa |
|---|---|
| **DỮ KIỆN (FACT)** | Được xác minh bằng cách đọc repository tại commit đã nêu, hoặc trích dẫn từ nguồn sơ cấp. Có thể tái lập. |
| **CÁCH DIỄN GIẢI (INTERPRETATION)** | Cách hiểu của tôi về ý nghĩa của dữ kiện. Có thể sai. |
| **KHUYẾN NGHỊ (RECOMMENDATION)** | Quan điểm thiết kế cho harness của chúng ta. Mang tính định hướng và chủ ý rõ ràng. |
| **CHƯA BIẾT (UNKNOWN)** | Khoảng trống được gọi tên; được liệt kê lại trong `OPEN_QUESTIONS.md`. |

---

## 0. Các Repository được kiểm tra, kèm Pinned Commit

| Dự án | Repo | Commit được kiểm tra | Ngày commit |
|---|---|---|---|
| Superpowers | `obra/superpowers` | `b36e0829c6d0140e93cfef2ca599b1b07d4a7797` (v6.3.0) | 2026-08-12 |
| Spec Kit | `github/spec-kit` | `e4842a03c830155e4c53315e4b8e32ef118d3f6e` | 2026-09-10 |
| OpenSpec | `Fission-AI/OpenSpec` | `9d4e5974e5c0d9a09b9c6c1e1eb0975e80ec4461` | 2026-09-09 |
| BMAD Method | `bmad-code-org/BMAD-METHOD` | `abe4eb1bce919c9d22cd18b3519353d5824c4b75` (6.13.0-next) | 2026-09-05 |
| SWE-agent | `SWE-agent/SWE-agent` | `3ea751c087f32b16e039a2233dd6eefecef325d5` | 2026-07-16 |
| mini-SWE-agent | `SWE-agent/mini-swe-agent` | `04d809ceab9df28f9adaed044884180159172930` | 2026-09-03 |
| GSD (đã archive) | `gsd-build/get-shit-done` | `bdcaab2c752d9a33a1a1ca9acf3a3c81fb991815` | 2026-05-31 |
| GSD Core (đang hoạt động) | `open-gsd/gsd-core` | `bcd99696d32cc919f82d9edefb1ce8ef68a05afc` | 2026-09-10 |

**DỮ KIỆN.** `gsd-build/get-shit-done` đã được lưu trữ (archived). Tệp `README.md` của nó viết: "Repository này không còn là ngôi nhà phát triển tích cực cho GSD. Dự án hiện tiếp tục dưới tên **GSD Core** tại repository Open GSD: `https://github.com/open-gsd/gsd-core`". Bất kỳ nghiên cứu nào chỉ đọc repository được nêu trong đề bài là đang đọc một ảnh chụp từ tháng 5/2026. Cả hai repo đều đã được đọc kỹ.

---

## 1. Phát hiện tiêu đề quan trọng nhất

**DỮ KIỆN.** Trong sáu dự án, chỉ có đúng một dự án cung cấp một kiểm tra xác định (deterministic), không dùng LLM để so sánh mã nguồn đã commit với mô tả hệ thống được lưu trữ: cổng codebase-drift của GSD (`gsd-core/src/drift.cts`, 431 dòng). Bề mặt phát hiện của nó gồm:

- một tệp mới được thêm vào mà tiền tố thư mục của nó không xuất hiện ở bất kỳ đâu trong `.planning/codebase/STRUCTURE.md` (`new_dir`);
- một export barrel mới được thêm vào khớp với `^(packages|apps)/[^/]+/src/index\.(ts|tsx|js|mjs|cjs)$`;
- một migration mới được thêm vào khớp với một trong bảy regex thư mục migration được hardcode;
- một module route mới được thêm vào dưới `routes/` hoặc `api/`.

Việc so khớp đối chiếu với `STRUCTURE.md` là `structureMd.includes(prefix)`. Tệp mã nguồn nêu rõ: "Việc so khớp có chủ ý dựa trên chuỗi con — STRUCTURE.md là markdown tự do, không phải một manifest có cấu trúc."

**DỮ KIỆN.** Mọi thứ khác mà sáu dự án gọi là phân tích tính nhất quán, xác minh, kiểm tra tính mạch lạc hay phát hiện độ lệch thực chất đều là một prompt. Lệnh `/speckit.analyze` của Spec Kit (`templates/commands/analyze.md`) là 100% các chỉ dẫn cho mô hình — script duy nhất của nó, `scripts/bash/check-prerequisites.sh`, chỉ phân giải thư mục feature và kiểm tra `[[ -f "$TASKS" ]]`. Skill `openspec-verify-change` của OpenSpec hướng dẫn mô hình "tìm kiếm trong codebase các từ khóa liên quan đến requirement" và "đánh giá xem việc triển khai có khả năng tồn tại hay không".

**CÁCH DIỄN GIẢI.** Lý do không phải vì lười biếng. Đó là vì Markdown tự do không thể kiểm tra tự động được, và mọi dự án trong số này đều chọn Markdown tự do làm định dạng tri thức của họ. Khoảnh khắc bạn viết `Payment Service → PostgreSQL` dưới dạng văn xuôi trong `architecture.md`, thứ duy nhất có thể so sánh nó với code là một mô hình ngôn ngữ. GSD có được một cổng kiểm soát xác định chính xác là bằng cách từ bỏ hoàn toàn ngữ nghĩa và kiểm tra một thứ thuần cấu trúc (thư mục này có xuất hiện ở đâu đó trong văn bản hay không).

**KHUYẾN NGHỊ.** Quyết định thiết kế trung tâm của harness của chúng ta *không phải* là chọn vòng đời nào. Đó là **làm cho một số lượng nhỏ các claim tri thức hệ thống có thể định địa chỉ bằng máy và kiểm tra được bằng máy, và chấp nhận rằng phần còn lại là văn xuôi chỉ có thể bị lỗi thời chứ không bao giờ có thể tự động kiểm chứng.** Mọi thứ khác trong tài liệu này đều bắt nguồn từ quyết định đó.

---

## 2. Bằng chứng cho thấy phát hiện độ lệch chỉ bằng LLM là nguyên thủy sai lầm

**DỮ KIỆN.** Ulfat, Sabit & Hossain, *Measuring LLM Trust Allocation Across Conflicting Software Artifacts*, arXiv:2604.03447 (nộp 2026-04-03, sửa đổi 2026-07-21). Nghiên cứu xây dựng các gói phương thức Java ghép cặp sạch/nhiễu (Javadoc, signature, implementation, test prefix), tiêm các lỗi đã biết vào tài liệu, phần triển khai, hoặc cả hai, và thu thập 22.339 phản hồi hợp lệ từ 7 LLM trên 456 gói. Trích nguyên văn từ bản tóm tắt:

> "các mô hình thể hiện sự bất đối xứng nguồn gốc nhất quán: chúng phát hiện lỗi tài liệu ở mức 67-94% và mâu thuẫn rõ ràng giữa tài liệu và triển khai ở mức 50-91%, nhưng khả năng phát hiện giảm từ 21-43 điểm phần trăm khi chỉ có phần triển khai thay đổi trong khi tài liệu vẫn giữ nguyên. Các mô hình cũng gặp khó khăn trong việc hạ mức ưu tiên các phần triển khai bị lỗi, và độ tự tin của mô hình hầu như không phân biệt được giữa các phán đoán đúng và sai trên sáu trong số bảy mô hình."

**CÁCH DIỄN GIẢI.** Điều này giáng đòn chí mạng trực tiếp vào phiên bản ngây thơ trong Mục 3 của bản tóm lược nhiệm vụ. Kịch bản trong đề bài — `architecture.md` nói PostgreSQL, mã nguồn hiện tại dùng Redis — *chính xác* là trường hợp "chỉ có phần triển khai thay đổi", vốn là trường hợp mà các mô hình kém hơn từ 21–43 điểm. Và "độ tự tin hầu như không phân biệt được giữa phán đoán đúng và sai" đồng nghĩa với việc bạn thậm chí không thể dùng độ tự tin của mô hình để quyết định khi nào cần leo thang lên con người.

**DỮ KIỆN.** Bài báo liên quan thứ hai: Macedo, *From Prompt to Process: a Process Taxonomy and Comparative Assessment of Frameworks Supporting AI Software Development Agents*, arXiv:2606.04967, so sánh OpenSpec, GitHub Spec-Kit, BMAD Method, Spec-Kitty, SpecFlow, GSD, ChatDev và SWE-agent. Các khoảng trống được báo cáo gồm "thiếu cơ chế duy trì tri thức kiến trúc xuyên suốt các giai đoạn phát triển", "không đủ khả năng truy vết giữa đặc tả và các artifact được sinh ra" và "xử lý không đầy đủ đối với độ lệch đặc tả khi yêu cầu phát triển".

**DỮ KIỆN.** Díaz, Gayoso, Cimminio & Pérez, *Spec-Driven Development for Agentic Software Engineering: Harnessing Human–Agent Teamwork*, arXiv:2609.00252v1 (2026-08-31, Universidad Politécnica de Madrid), đề xuất một harness tám cơ chế: H1 context engineering, H2 tri thức chia sẻ bền vững, H3 đặc tả thực thi được, H4 agent song song N-phiên bản, H5 đặc tả quy chuẩn, H6 tham vấn có cấu trúc, H7 nghiệm thu dựa trên bằng chứng, H8 tự chủ từng cấp độ. Nó định nghĩa đặc tả cần phải *thực thi được*, *tường minh*, *có thể truy vết* và *có thể giải tỏa bằng bằng chứng*, và liệt kê một bài toán mở là "duy trì tính nhất quán giữa đặc tả, tri thức hệ thống và code ở quy mô lớn". Các tác giả mô tả công trình này là "bước đầu tiên hướng tới sự đồng thuận học thuật - công nghiệp, thay vì một lý thuyết đã được kiểm chứng hoàn toàn."

**CÁCH DIỄN GIẢI.** Giới học thuật đã độc lập đi đến hình thái gần như tương tự như những gì bản tóm lược phác thảo, và độc lập chỉ ra cùng một phần chưa có lời giải. Chưa ai giải quyết được việc đồng bộ hóa tri thức. Chúng ta cũng không nên lên kế hoạch giải quyết nó tuyệt đối — chúng ta nên lên kế hoạch *khoanh vùng và kiểm soát (contain)* nó.

**KHUYẾN NGHỊ.** Tiếp thu ba quy tắc cứng từ bằng chứng này:

1. **Phát hiện lỗi thời bắt buộc phải mang tính xác định; phán đoán tính đúng đắn có thể được LLM hỗ trợ nhưng bắt buộc phải do con người phê duyệt.** Không bao giờ hỏi mô hình "tài liệu này có còn đúng không?" như một cổng kiểm soát.
2. **Tuyệt đối không cho phép tự động đối soát tài liệu theo code.** Sự bất đối xứng của bài báo chỉ ra rằng mô hình sẽ ưu tiên "sửa" tài liệu, vốn là phần sai lầm trong chính trường hợp chúng ta quan tâm nhất.
3. **Ưu tiên các claim mà một công cụ có thể bác bỏ (falsify)** (một rule phụ thuộc, một bản diff OpenAPI, một bài test có tên) hơn là các claim mà chỉ mô hình mới đánh giá được.

---

## 3. Superpowers

### 3.1 Các dữ kiện thực tế

**DỮ KIỆN.** 14 skill, tổng cộng 3.377 dòng `SKILL.md`. Danh sách đầy đủ kèm số dòng:
`using-superpowers` (63), `executing-plans` (64), `requesting-code-review` (95),
`verification-before-completion` (120), `dispatching-parallel-agents` (167), `using-git-worktrees` (167),
`writing-plans` (171), `receiving-code-review` (205), `finishing-a-development-branch` (225),
`brainstorming` (250), `systematic-debugging` (283), `test-driven-development` (320),
`subagent-driven-development` (568), `writing-skills` (679).

**DỮ KIỆN.** Cơ chế thực thi là một hook `SessionStart` (`hooks/hooks.json`, bộ so khớp `startup|clear|compact`) gọi script `hooks/session-start`, đọc `skills/using-superpowers/SKILL.md` và bơm vào làm `additionalContext` được bọc trong thẻ `<EXTREMELY_IMPORTANT>`. Skill đó chứa nội dung:

> "Nếu bạn nghĩ có dù chỉ 1% khả năng một skill có thể áp dụng cho những gì bạn đang làm, bạn TUYỆT ĐỐI BẮT BUỘC PHẢI gọi skill đó. NẾU MỘT SKILL ÁP DỤNG CHO TÁC VỤ CỦA BẠN, BẠN KHÔNG CÓ SỰ LỰA CHỌN. BẠN BẮT BUỘC PHẢI SỬ DỤNG NÓ."

**DỮ KIỆN.** Không có tệp trạng thái, không có registry artifact, không có CLI, không có validator. Trạng thái là: kế hoạch markdown trong `docs/superpowers/plans/YYYY-MM-DD-<feature>.md`, tài liệu thiết kế trong `docs/superpowers/specs/`, git worktrees, và các ô checkbox `- [ ]` bên trong kế hoạch.

**DỮ KIỆN.** `brainstorming` triển khai một bộ định tuyến quy mô ba hướng — **spike** / **bounded** / **architectural** — kèm cơ chế bánh cóc một chiều tường minh: "sự phức tạp tiềm ẩn được phát hiện giữa chừng sẽ nâng cấp lộ trình — dừng lại, thông báo, và bước lên. Không có gì được hạ cấp giữa chừng." Chỉ có lộ trình *architectural* mới tạo ra một tệp spec bằng văn bản và bàn giao sang `writing-plans`.

**DỮ KIỆN.** `brainstorming` mang một cổng phê duyệt vô điều kiện: `<HARD-GATE>` "TUYỆT ĐỐI KHÔNG gọi bất kỳ skill triển khai nào, không viết bất kỳ dòng code nào, không scaffold bất kỳ dự án nào, hoặc thực hiện bất kỳ hành động triển khai nào cho đến khi bạn đã nói rõ với đối tác con người về ý định của mình và họ đã phê duyệt nó." Cộng thêm một bảng chống phản khuôn mẫu rõ ràng ("Cái này quá đơn giản để cần thiết kế" → "Đơn giản nghĩa là một bản thiết kế ngắn, không phải là không có thiết kế").

**DỮ KIỆN.** `writing-plans` bắt buộc tiêu đề kế hoạch phải chứa `Goal`, `Architecture`, `Tech Stack`, `Spec` (đường dẫn tới tài liệu mà kế hoạch triển khai) và `Global Constraints`; các khối theo từng task chứa `Files:` (Create/Modify kèm khoảng dòng/Test), `Interfaces: Consumes/Produces` kèm chữ ký hàm chính xác, và 5 bước TDD checkbox kèm code nguyên văn trong mỗi bước. Nó cấm các placeholder rõ ràng: "TBD", "thêm xử lý lỗi thích hợp", "Tương tự Task N", "Viết test cho phần trên (mà không có code test thực tế)".

**DỮ KIỆN.** `subagent-driven-development` (skill workflow lớn nhất) điều phối một subagent triển khai tươi mới cho mỗi task, sau đó review 2 giai đoạn (tuân thủ spec, sau đó đến chất lượng code), rồi review toàn bộ branch. Nó cấm việc dừng lại hỏi con người giữa các task: "Phán quyết, không đình trệ. Một kế hoạch đang chạy không chờ đợi con người."

**DỮ KIỆN.** `verification-before-completion` phát biểu quy tắc: "KHÔNG CÓ TUYÊN BỐ HOÀN THÀNH NẾU THIẾU BẰNG CHỨNG KIỂM CHỨNG TƯƠI MỚI … Nếu bạn chưa chạy lệnh xác minh trong chính tin nhắn này, bạn không thể khẳng định nó đã pass."

**DỮ KIỆN.** `writing-skills` áp dụng TDD vào việc viết prompt: viết các kịch bản áp lực, quan sát một subagent thất bại khi không có skill (ĐỎ), viết skill, quan sát nó tuân thủ (XANH), sau đó bịt các lỗ hổng. Có một thư mục `tests/` với các bộ test suite theo từng host (`tests/claude-code`, `tests/codex`, `tests/hooks`, `tests/explicit-skill-requests/prompts`, …).

**DỮ KIỆN.** Hạn chế đã biết, được nêu trong README: một số nền tảng host thiếu các hook sau khi nén ngữ cảnh (post-compaction hooks), do đó chỉ dẫn bootstrap có thể bị mất trong các phiên làm việc dài.

### 3.2 Cách diễn giải

**CÁCH DIỄN GIẢI.** Superpowers là một harness mang tính *hành vi*, không phải harness mang tính *cấu trúc*. Nó thay đổi những gì agent làm bằng cách biến các chỉ dẫn thành mệnh lệnh to tiếng và vô điều kiện, và bằng cách cô lập ngữ cảnh trong các subagent. Nó hoàn toàn không có khái niệm về hệ thống đang được xây dựng. Không có tài liệu kiến trúc, không có mô hình component, không có bất biến, không có ADR, không có kiểm định chéo giữa các artifact. Nó là một thư viện kỷ luật.

**CÁCH DIỄN GIẢI.** Ý tưởng kỹ nghệ có thể chuyển giao tốt nhất của nó không phải là bất kỳ skill đơn lẻ nào; mà là **skills-as-tested-artifacts (các skill như những artifact đã qua kiểm thử)**. Một prompt có bộ test suite đỏ/xanh thực sự là một artifact kỹ nghệ. Một prompt không có test suite chỉ là truyền thuyết dân gian. Đây là dự án duy nhất trong tập hợp coi prompt của chính mình là thứ có thể kiểm thử được.

**CÁCH DIỄN GIẢI.** Ý tưởng có thể chuyển giao thứ hai là **bộ định tuyến quy mô kèm bánh cóc một chiều**. Đây là câu trả lời ít tốn kém nhất cho lời chỉ trích "phát triển theo spec quá nặng nề cho một dòng sửa đổi", và nó chỉ là một skill, không phải là cả một framework đồ sộ.

**CÁCH DIỄN GIẢI.** Phong cách viết hoa cưỡng chế `<EXTREMELY-IMPORTANT>` / "bạn không có sự lựa chọn" là một triệu chứng, không phải một thiết kế. Nó tồn tại vì các chỉ dẫn bằng prompt không thể cưỡng chế thực thi. Mọi sự leo thang về mặt câu chữ là bằng chứng cho thấy cơ chế đang nằm sai tầng. Ở nơi nào chúng ta có thể chuyển một quy tắc thành một script trả về mã thoát khác 0, chúng ta nên làm như vậy, và khi đó việc gào thét là hoàn toàn không cần thiết.

### 3.3 Tiếp thu / Từ chối

**Tiếp thu:** bộ định tuyến quy mô + bánh cóc 1 chiều; định dạng kế hoạch (`Files` / `Interfaces Consumes-Produces` / không-placeholder); bằng-chứng-trước-khẳng-định như một luật thép; subagent-tươi-mới-cho-mỗi-task để cô lập ngữ cảnh; review 2 giai đoạn (tuân thủ spec tách biệt với chất lượng code); TDD-cho-prompts với một thư mục test thực sự; quy ước "công bố tên skill bạn đang dùng" (tăng khả năng quan sát với chi phí rẻ).

**Từ chối:** sử dụng câu chữ in hoa cưỡng chế làm tầng thực thi chính; "không bao giờ dừng lại hỏi con người giữa kế hoạch" (chúng ta muốn *ít* cổng kiểm soát, không phải *không có* cổng nào — xem §16 của bản tóm lược và `WORKFLOW.md`); sự vắng bóng hoàn toàn của mô hình hệ thống; giả định của luồng brainstorming→plan rằng một tài liệu thiết kế cộng với một bản kế hoạch là đủ tri thức bền vững (nó là tri thức theo từng thay đổi và nó mục rữa ngay khoảnh khắc thay đổi đó được merge).

**Chỉnh sửa:** `verification-before-completion` nên trở thành một lệnh xác định (`forge verify`) tạo ra một artifact bằng chứng cụ thể, không phải là một skill nhắc nhở mô hình hãy trung thực.

---

## 4. GitHub Spec Kit

### 4.1 Các dữ kiện thực tế

**DỮ KIỆN.** Tập lệnh (từ `templates/commands/*.md`): `constitution`, `specify`, `clarify`, `plan`, `tasks`, `analyze`, `checklist`, `implement`, `converge`, `taskstoissues`. Cấu trúc thư mục được tạo bởi `specify init`: `.specify/` (config, `memory/constitution.md`, `templates/overrides/`, `presets/templates/`, `extensions/templates/`) và `specs/NNN-xxx/`.

**DỮ KIỆN.** Các artifact theo từng tính năng (từ `templates/plan-template.md`): `plan.md`, `research.md` (phase 0), `data-model.md` (phase 1), `quickstart.md` (phase 1), `contracts/` (phase 1), `tasks.md` (phase 2). `spec.md` sinh ra từ `/speckit.specify`.

**DỮ KIỆN.** Cấu trúc `spec-template.md`: các user story được ưu tiên hóa (P1/P2/P3), mỗi story có **Tại sao ưu tiên mức này (Why this priority)**, **Kiểm thử độc lập (Independent Test)** và các kịch bản nghiệm thu Given/When/Then; Các trường hợp biên (Edge Cases); Yêu cầu chức năng dạng `FR-001 … FR-00n` với `System MUST …`; Các thực thể chính; Tiêu chí thành công dạng `SC-001 …` ("có thể đo lường" và "không phụ thuộc công nghệ"); Các giả định. Những mục chưa giải quyết được đánh dấu nội dòng là `[NEEDS CLARIFICATION: …]`.

**DỮ KIỆN.** Hiến chương nằm tại `.specify/memory/constitution.md` và được tuyên bố là không thể thương lượng bên trong `analyze.md`: "Xung đột với hiến chương tự động bị coi là CRITICAL và đòi hỏi phải điều chỉnh spec, plan hoặc tasks — tuyệt đối không làm loãng, diễn giải lại hoặc âm thầm phớt lờ nguyên tắc."

**DỮ KIỆN.** Bản hiến chương của chính repository này (`.specify/memory/constitution.md`) mở đầu bằng khối comment `SYNC IMPACT REPORT` ghi nhận việc nâng phiên bản, lý do nâng, các nguyên tắc được định nghĩa, các phần được thêm vào, và một checklist ghi rõ *những template hạ nguồn nào đã được review để đảm bảo tính đồng bộ* kèm các dấu ✅ và số dòng tham chiếu.

**DỮ KIỆN.** Các lượt quét của `/speckit.analyze`: trùng lặp, mơ hồ (các tính từ mơ hồ "nhanh, có thể mở rộng, bảo mật, trực quan, mạnh mẽ" thiếu tiêu chí đo lường; các placeholder chưa giải quyết `TODO/TKTK/???`), thiếu đặc tả, căn chỉnh với hiến chương, khoảng trống bao phủ (yêu cầu không có task nào, task không gắn với yêu cầu nào), không nhất quán (lệch pha thuật ngữ, thực thể trong plan vắng bóng trong spec, mâu thuẫn về thứ tự task, các yêu cầu xung đột nhau). Thang đo mức độ nghiêm trọng CRITICAL/HIGH/MEDIUM/LOW. Đầu ra là một bản báo cáo; lệnh này mang tính `STRICTLY READ-ONLY` và bắt buộc "KHÔNG BAO GIỜ sửa đổi tệp". Giới hạn tối đa 50 phát hiện. Nó cũng hỏi "Bạn có muốn tôi đề xuất các chỉnh sửa khắc phục cụ thể cho N vấn đề hàng đầu không?" và không được tự ý áp dụng chúng.

**DỮ KIỆN.** `/speckit.analyze` xây dựng một "Danh mục yêu cầu (Requirements inventory)" dựa trên các khóa `FR-###`/`SC-###` và một "Bản đồ bao phủ task (Task coverage mapping)" bằng cách "suy luận theo từ khóa / các mẫu tham chiếu rõ ràng như ID hoặc cụm từ khóa".

**DỮ KIỆN.** Mã nguồn thực thi duy nhất trong toàn bộ workflow là phân giải đường dẫn và kiểm tra sự tồn tại của tệp: `check-prerequisites.sh` (`--require-spec`, `--require-tasks`, `--paths-only`, `--template NAME`), `common.sh` (tìm thư mục gốc repo bằng cách duyệt lên tìm `.specify/`, phân giải feature qua `SPECIFY_FEATURE` hoặc `.specify/feature.json`), `create-new-feature.sh`, `setup-plan.sh`, `setup-tasks.sh`, và `resolve-template.sh` (ngăn xếp ghi đè template: ghi đè của dự án → presets → extensions → tích hợp sẵn).

**DỮ KIỆN.** Tệp `tasks-template.md` nêu rõ: "**Tests**: Các ví dụ bên dưới bao gồm các task kiểm thử. Tests là TÙY CHỌN (OPTIONAL) - chỉ đưa vào nếu được yêu cầu rõ ràng trong bản đặc tả tính năng."

**DỮ KIỆN.** Có một hệ thống hook mở rộng: `.specify/extensions.yml` với các khóa `hooks.before_analyze` / `hooks.after_analyze`, mỗi hook có `enabled`, `optional`, `condition`, `command`, `prompt`. Đáng chú ý, tệp lệnh chỉ dẫn *mô hình* đọc YAML rồi in ra dòng `EXECUTE_COMMAND:` — việc điều phối hook được thực hiện qua prompt, không phải qua engine của công cụ.

**DỮ KIỆN.** Hoàn toàn không có tầng tri thức hệ thống. Extension `extensions/agent-context/` có script `update-agent-context.sh`, vốn chỉ duy trì các tệp chỉ dẫn cho agent; không có kho lưu trữ kiến trúc, component, invariant, ADR hay mô hình dữ liệu nào tồn tại lâu hơn một thư mục feature.

### 4.2 Cách diễn giải

**CÁCH DIỄN GIẢI.** Đóng góp thực sự của Spec Kit là **từ vựng artifact và tính kỷ luật của template**, không phải cơ chế thực thi. `FR-###`, `SC-###`, `[NEEDS CLARIFICATION]`, các user story được ưu tiên và có thể kiểm thử độc lập, và một bản hiến chương dự án có hiệu lực cao hơn spec — đó là những thứ tốt, chi phí rẻ và phần lớn không phụ thuộc ngôn ngữ.

**CÁCH DIỄN GIẢI.** `/speckit.analyze` là bản *đặc tả* đầy đủ nhất về một engine kiểm tra tính nhất quán trong toàn bộ tài liệu tham chiếu và đồng thời là minh chứng rõ ràng nhất cho thấy tại sao prompt lại là phương thức triển khai sai lầm cho nó. Hãy nhìn vào những gì nó yêu cầu mô hình làm: dựng một danh mục yêu cầu, ánh xạ task tới yêu cầu bằng suy luận từ khóa, tính toán tỷ lệ bao phủ, và tạo ra "kết quả mang tính xác định: chạy lại mà không sửa gì phải tạo ra các ID và số lượng nhất quán". Mỗi việc trong số đó đều là một script 5 dòng quét qua các ID có nhãn rõ ràng. Yêu cầu một mô hình làm tính số học trên các ID mà nó trích xuất bằng suy luận từ khóa là tệ hơn rất nhiều so với việc grep tìm các ID đó.

**CÁCH DIỄN GIẢI.** Điểm đánh dấu `[NEEDS CLARIFICATION: …]` chưa được đánh giá đúng mức. Nó là một *điểm đánh dấu sự không chắc chắn nội dòng, có thể grep được bằng máy*. Một script có thể đếm chúng và từ chối cho phép chuyển phase. Đó là một cổng kiểm soát thực sự được xây dựng từ một quy ước chuỗi ký tự — dạng thực thi rẻ nhất có thể có.

**CÁCH DIỄN GIẢI.** Việc tuyên bố "Tests là TÙY CHỌN" là một khiếm khuyết lớn. Bản template spec của chính Spec Kit đòi hỏi `Independent Test` cho mỗi story và tiêu chí `SC-###` có thể đo lường, rồi sau đó template task lại biến test thành tùy chọn. Khi đó không có gì giải tỏa các kịch bản nghiệm thu. Đây chính là điểm đứt gãy truy vết mà nghiên cứu arXiv:2606.04967 đã báo cáo cho toàn bộ nhóm công cụ này.

**CÁCH DIỄN GIẢI.** Khối `SYNC IMPACT REPORT` là một hạt giống quý: khi một tài liệu chi phối thay đổi, thay đổi đó mang theo một danh sách mà máy có thể đọc được ghi rõ các artifact hạ nguồn đã được kiểm tra lại. Đó chính là mầm mống của một bản ghi nhận tác động chuẩn mực.

### 4.3 Tiếp thu / Từ chối

**Tiếp thu:** các ID yêu cầu ổn định và có nhãn (`FR-###` / `SC-###`); `[NEEDS CLARIFICATION]` làm điểm đánh dấu chặn có thể grep được; các story được ưu tiên và có thể kiểm thử độc lập; hiến chương có hiệu lực cao hơn spec; ngăn xếp ghi đè template (dự án có thể ghi đè template tích hợp sẵn mà không cần fork); ý tưởng `SYNC IMPACT REPORT`, được tổng quát hóa thành artifact impact theo từng thay đổi; tính chất chỉ-đọc của phase phân tích (chỉ báo cáo, không bao giờ tự sửa tệp).

**Từ chối:** thư mục `specs/NNN-feature/` được đánh số đóng vai trò đơn vị công việc (nó không bao giờ hội tụ thành tri thức hệ thống — xem §6); điều phối hook qua prompt; bộ 6 tệp lập kế hoạch cho mỗi tính năng (`research.md`, `quickstart.md`, `data-model.md`, `contracts/` theo từng feature) — phần lớn trong số đó hoặc là tri thức hệ thống đáng lẽ phải mang tính vĩnh viễn hoặc là tiếng ồn không nên tồn tại; test tùy chọn; triển khai `analyze` dưới dạng một prompt.

**Chỉnh sửa:** `analyze` được chia thành `forge check` (mang tính xác định: độ bao phủ ID, task mồ côi, quét placeholder, độ lỗi thời neo, các quy tắc hiến chương đã cơ giới hóa) cộng với một đợt review bằng LLM nhỏ gọn hơn nhiều chỉ xử lý các câu hỏi ngữ nghĩa thực chất (yêu cầu này có kiểm thử được không? hai yêu cầu này có xung đột ý nghĩa không?).

---

## 5. BMAD Method

### 5.1 Các dữ kiện thực tế

**DỮ KIỆN.** 29 skills, 257 tệp, **2.4 MB** dung lượng nội dung skill. Danh sách skills: `bmad`, `bmad-advanced-elicitation`, `bmad-agent-analyst`, `bmad-agent-architect`, `bmad-agent-dev`, `bmad-agent-pm`, `bmad-agent-ux-designer`, `bmad-architecture`, `bmad-brainstorming`, `bmad-build`, `bmad-build-auto`, `bmad-code-review`, `bmad-correct-course`, `bmad-create-epics-and-stories`, `bmad-customize`, `bmad-deep-recon`, `bmad-forge-idea`, `bmad-party-mode`, `bmad-prd`, `bmad-prfaq`, `bmad-product-brief`, `bmad-project-context`, `bmad-qa-generate-e2e-tests`, `bmad-retrospective`, `bmad-review`, `bmad-spec`, `bmad-sprint-planning`, `bmad-ux`, `bmad-walkthrough`.

**DỮ KIỆN.** Các nhân cách agent tồn tại dưới dạng *skills* (`bmad-agent-analyst`, `-architect`, `-dev`, `-pm`, `-ux-designer`), không phải các tiến trình riêng biệt. Việc khám phá dựa vào `module-manifest.toml` bên cạnh mỗi skill, chứa `module`, `version`, `update_source`, và một trường văn bản tự do `knowledge` trỏ tới một tài liệu điều hướng (tất cả các manifest được kiểm tra đều trỏ tới "`references/help.md` trong skill `bmad`").

**DỮ KIỆN.** Cấu hình được phân giải bằng các script, không phải qua prompt: `_bmad/scripts/resolve_customization.py --skill … --key workflow` và `_bmad/scripts/resolve_config.py --project-root …` (hợp nhất `_bmad/config.toml` với các cấu hình ghi đè trong `_bmad/custom/`). Các skill khai báo `activation_steps_prepend` / `activation_steps_append` / `persistent_facts` (kèm các mục `file:` được nạp) trong `customize.toml`.

**DỮ KIỆN — artifact giá trị nhất trong toàn bộ tài liệu tham chiếu.** Skill `bmad-architecture` cung cấp `assets/spine-template.md`, một bản "Architecture Spine" với YAML frontmatter (`type: architecture-spine`, `purpose`, `altitude: initiative|feature|epic`, `paradigm`, `scope`, `status`, `binds: []`, `sources: []`, `companions: []`) và các phần sau: Design Paradigm; Inherited Invariants; **Invariants & Rules**; Consistency Conventions; Stack; Structural Seed; Capability → Architecture Map; Deferred.

Mỗi khối quyết định kiến trúc có một hình thái cố định:

```
### AD-1 — {decision}
- **Binds:** {capability / unit ids / fr/nfr's, areas, hoặc `all`}
- **Prevents:** {sự phân kỳ mà quyết định này ngăn chặn}
- **Rule:** {ràng buộc mà các khâu hạ nguồn bắt buộc phải tuân theo}
```

Tiêu chí kết nạp của chính template này cho mục Invariants là, nguyên văn: *"Trái tim bền vững: những quyết định mà người xây dựng trong tương lai không thể đọc ra từ code chuẩn mực."* Mục Stack của nó được chú thích: *"HẠT GIỐNG (SEED) — được xác minh là đúng tại thời điểm viết; mã nguồn nắm giữ chi tiết này một khi nó tồn tại."* Mục Structural Seed: *"Mã nguồn sở hữu chi tiết — đây là khung giàn giáo, không phải một tấm gương phản chiếu để phải duy trì."* Các ID AD là "id tăng dần ổn định (không bao giờ tái sử dụng/đánh số lại)". Các invariant kế thừa là "chỉ đọc, không bao giờ đánh số lại, không phái sinh lại. Một quyết định cục bộ mâu thuẫn với nó là một xung đột cần làm nổi lên, không phải là một sự ghi đè."

**DỮ KIỆN.** Template đó có một **doc linter mang tính xác định**: `bmad-architecture/scripts/lint_spine.py` (270 dòng, kèm các bài test). Docstring của nó nêu rõ sự phân định: *"LLM đếm sai ID và bỏ sót các placeholder nguyên văn; grep thì không. Linter này sở hữu các kiểm tra mà một script làm tốt hơn một prompt, và để lại nửa phần ngữ nghĩa (mỗi Rule có thực sự thực thi được không? ranh giới có hợp lý không?) cho người duyệt tiêu chí rubric."* Các kiểm tra: `placeholder` (chữ TBD/TODO/FIXME/XXX nguyên văn, "tương tự AD-n", `{template-token}` chưa điền), `ad_id` (trùng lặp hoặc số AD không tăng dần), `ad_fields` (một khối AD thiếu Binds/Prevents/Rule), `version_pin` (một hàng trong `## Stack` nêu tên một thứ nhưng không có phiên bản). Các khối code fence được làm trắng trước khi quét để sơ đồ mermaid và cây thư mục nguồn không tạo ra dương tính giả trong khi số dòng vẫn hoàn toàn chuẩn xác. Mã thoát luôn là 0; các phát hiện được trả về dưới dạng JSON và bên gọi sẽ quyết định.

**DỮ KIỆN.** `bmad-spec` sử dụng một mô hình phái sinh: `.memlog.md` là "chuẩn tắc — một bản ghi nhật ký append-only, theo thứ tự thời gian của mọi quyết định, ràng buộc, năng lực (kèm `CAP-N` ổn định của nó), giả định, câu hỏi mở … không bao giờ được chỉnh sửa hay sắp xếp lại", và `SPEC.md` cùng các tệp đi kèm được "**phái sinh ở mỗi lần chạy** từ memlog". Lý do được đưa ra: *"Việc phái sinh hợp đồng từ một living log thay vì chỉnh sửa hợp đồng tại chỗ là thứ giúp các bước xung quanh spec (PRD, UX, kiến trúc, epics) có thể chạy theo bất kỳ thứ tự nào và cùng nạp vào một spec mà không bị lệch khi merge: log chỉ tích lũy thêm, artifact được render lại."* `bmad-spec` được tuyên bố là bên ghi duy nhất; việc sửa tay từ bên ngoài vào `SPEC.md` là "không được hỗ trợ và sẽ bị ghi đè trong lần phái sinh tiếp theo". Việc ghi đi qua script `_bmad/scripts/memlog.py` (nguyên tử).

**DỮ KIỆN — chính sách tuyển chọn tri thức xuất sắc nhất.** `bmad-project-context` duy trì một khối được quản lý bên trong `AGENTS.md` được phân tách bởi `<!-- bmad:context -->` / `<!-- /bmad:context -->` với dòng xuất xứ: `<!-- Verified 2026-08-08 against a1b2c3d. Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->`

Quy trình refresh: "Đọc dòng xuất xứ, xác minh lại mọi đường dẫn và mọi lưu ý, và chạy `git log --diff-filter=DR --name-only` kể từ SHA đã ghi nhận đối chiếu với từng dòng — cập nhật hoặc xóa bỏ các dòng mà bằng chứng của chúng đã biến mất."

Việc xóa bỏ bắt buộc phải dựa trên một trong đúng bốn căn cứ:

> 1. **Lỗi thời hoặc sai lệch** — đối tượng tham chiếu đã biến mất, hoặc chỉ dẫn chưa bao giờ đúng; bằng chứng được nêu tên cụ thể.
> 2. **Được thực thi bằng cơ học** — một hook, linter, formatter, hoặc kiểm tra CI đã làm thất bại chính xác vi phạm mà chỉ dẫn nêu tên. Một công cụ chỉ đơn thuần bao phủ cùng tệp hoặc cùng chủ đề thì không được tính là thực thi chỉ dẫn.
> 3. **Có hại hoặc mâu thuẫn** — nó trỏ agent vào sai thứ, hoặc nó mâu thuẫn với một chỉ dẫn đang hiệu lực khác và bị thua trong quá trình đối soát.
> 4. **Người dùng đã phê duyệt việc xóa bỏ này** — được hỏi dưới dạng một mục riêng biệt, không bao giờ được ngầm định bằng việc phê duyệt một khối thay thế.

Và, nguyên văn: *"Tính ngắn gọn không phải là căn cứ, dạo này không thấy cái gì bị fail không phải là căn cứ, 'agent có thể tự suy ra được' không phải là căn cứ, và **'nó có thể tự khám phá ở đâu đó trong repository' tuyệt đối không bao giờ tự thân nó là căn cứ** — đó chính là kiểu lý luận làm rỗng những tệp tài liệu tốt."*

Các quy tắc khác từ cùng skill: mọi thao tác ghi đều phải có một **sổ cái (ledger)** đi trước với một mục cho mỗi chỉ dẫn hiện có được phân loại thành `retain | rewrite | relocate | automate | delete` kèm bằng chứng và rủi ro; "Đối với mỗi ứng viên, hãy tự hỏi trước liệu một hook, quy tắc lint, hay kiểm tra CI có thực thi nó tốt hơn văn xuôi hay không; nếu có hãy đề xuất bài kiểm tra đó, và dòng văn xuôi chỉ là phương án dự phòng nếu họ từ chối"; "Không bao giờ hỏi những gì một lệnh quét có thể trả lời. Yêu cầu người dùng xác nhận một khẳng định đã được kiểm tra qua đường dẫn … là một khiếm khuyết"; một ngân sách kích thước trong đó "Vượt ngân sách đồng nghĩa với việc cắt giảm các dòng yếu nhất hoặc chuyển chúng ra sau một trigger — tuyệt đối không bao giờ nâng ngân sách"; và một quy tắc truy xuất: "Một chỉ mục mà agent phải tự chọn để fetch sẽ bị bỏ qua; một chỉ mục đã nằm sẵn trong ngữ cảnh thì không."

**DỮ KIỆN.** Skill router `bmad` mang tính chỉ đọc rõ ràng đối với các yêu cầu trợ giúp và từ chối đoán mò: "Nếu điều gì đó không thể đọc được, hãy nói rõ và không được đoán."

### 5.2 Cách diễn giải

**CÁCH DIỄN GIẢI.** BMAD thực chất là hai dự án nằm trong một repository. Có một bộ lập kế hoạch đồ sộ, nhiều nghi thức, dựa trên vai diễn (PRD, PRFAQ, product brief, sprint planning, party mode, năm nhân cách agent), và có một hạt nhân nhỏ về kỹ nghệ tri thức thực sự xuất sắc (`spine-template.md` + `lint_spine.py`, phái sinh `.memlog.md`, sổ cái của `project-context` và bốn căn cứ xóa bỏ). Phần thứ hai chính là lý do để đọc BMAD.

**CÁCH DIỄN GIẢI — ý tưởng quan trọng nhất tôi tìm thấy.** *"Những quyết định mà người xây dựng trong tương lai không thể đọc ra từ code chuẩn mực"* chính là tiêu chí kết nạp còn thiếu cho tri thức hệ thống. Nó trả lời câu hỏi của bản tóm lược "những gì thực sự nên lưu trữ so với những gì nên khám phá động" trong một câu duy nhất, và nó có thể bác bỏ được: đối với bất kỳ dòng ứng viên nào, hãy tự hỏi "nếu tôi xóa dòng này và đưa cho một kỹ sư có năng lực đoạn code, liệu họ có trích xuất lại được nó không?" Nếu có, nó là thông tin phái sinh, không phải tri thức. Điều này giúp loại bỏ phần lớn tiếng ồn của tài liệu do AI tạo ra, bởi vì các tài liệu kiến trúc do AI viết hầu như chỉ nhắc lại những gì code đã thể hiện rõ ràng.

**CÁCH DIỄN GIẢI.** Bộ ba `Binds` / `Prevents` / `Rule` là *hình thái* chuẩn xác cho một claim kiến trúc, và nó gần như có thể thực thi được. `Rule` là ràng buộc; `Binds` là phạm vi; `Prevents` là bài kiểm tra bác bỏ. Một quy tắc có phạm vi `Binds` và một `Rule` có thể thực thi chỉ cách một bước ngắn để có thể biên dịch thành một rule của dependency-cruiser / ArchUnit / Tach. Bước ngắn đó chính là toàn bộ cơ hội của chúng ta.

**CÁCH DIỄN GIẢI.** Khuôn mẫu memlog append-only + artifact phái sinh giải quyết một bài toán mà bản tóm lược không nhắc tên nhưng sẽ gặp phải ngay lập tức: **ai sở hữu tệp**. Nếu cả con người và nhiều skill cùng sửa `architecture.md` tại chỗ, bạn sẽ gặp tình trạng lệch khi merge và mất dấu xuất xứ. Nếu các quyết định tích lũy trong một log append-only và tài liệu được render lại, nguồn gốc xuất xứ là miễn phí và xung đột thứ tự biến mất. Chi phí phải trả là tài liệu được render tuyệt đối không bao giờ được sửa tay, đó là một bài toán kỷ luật, và nó nhân đôi số lượng artifact.

**CÁCH DIỄN GIẢI.** Bốn căn cứ để xóa bỏ là câu trả lời đúng đắn cho câu hỏi của bản tóm lược "hệ thống ngăn chặn tài liệu biến thành rác vô dụng do AI sinh ra như thế nào?" — nhưng hãy lưu ý rằng chúng cũng giải quyết thất bại ở *chiều ngược lại*, và đó là rủi ro tinh vi hơn. Một agent được yêu cầu "dọn dẹp tài liệu" sẽ xóa đi những tri thức đúng đắn, mang tính trụ cột chỉ vì chúng không được sử dụng rõ ràng ở bề nổi. Câu nói "Nó có thể tự khám phá được ở đâu đó trong repository tuyệt đối không bao giờ tự thân nó là căn cứ" chính là rào chắn ngăn một mô hình thích dọn dẹp làm sạch bách tệp tài liệu quý giá.

**CÁCH DIỄN GIẢI.** Chi phí của BMAD là khổng lồ. 2.4 MB các skill, một bộ phân giải cấu hình bằng Python, một manifest TOML cho mỗi skill, năm nhân cách, và một builder để tiếp tục tạo thêm. Đối với một lập trình viên cá nhân đây là một gánh nặng: mỗi dòng đều phải trả giá trong ngữ cảnh hoặc trong sự gián tiếp, và bề mặt có thể mục rữa tỷ lệ thuận với kích thước. Tài liệu `best-practices.md` của chính BMAD đã nói điều này tốt hơn tôi: "Mỗi dòng đều phải trả giá trong mọi phiên làm việc, và khả năng tuân thủ chỉ dẫn suy giảm khi tập nạp mở rộng."

**CÁCH DIỄN GIẢI về câu hỏi các nhân cách (personas).** Các nhân cách của BMAD thực chất chỉ là các skill nằm trong một agent duy nhất, không phải các agent riêng biệt. Giá trị quan sát được của `bmad-agent-architect` so với một skill tên là `design` chỉ là một system prompt khác đi và một checklist khác đi. Hoàn toàn không có bằng chứng nào trong repository cho thấy việc nhập vai giúp cải thiện kết quả; giá trị nằm ở checklist. **Nhiều agent chỉ phát huy giá trị cho việc cô lập ngữ cảnh và chạy song song, không phải cho tính cách vai diễn.**

### 5.3 Tiếp thu / Từ chối

**Tiếp thu:** tiêu chí kết nạp ("không thể đọc ra từ code chuẩn mực"); cấu trúc `AD-n` với Binds/Prevents/Rule và các ID ổn định không bao giờ đánh số lại; doc linter xác định và sự phân tách cơ học/ngữ nghĩa rõ ràng của nó; các invariant kế thừa là chỉ-đọc; các chú thích nguồn chân lý kiểu `Stack`-là-hạt-giống / `code owns the detail`; dòng xuất xứ (`Verified <date> against <sha>`) cộng với việc tái xác minh `git log --diff-filter=DR`; bốn căn cứ xóa bỏ và sổ cái; "ưu tiên một kiểm tra tự động hơn một quy tắc văn xuôi"; ngân sách kích thước không có lối thoát hiểm; log quyết định append-only với render phái sinh; độ cao altitude (initiative/feature/epic) làm sự thích ứng quy mô; bảng `Capability → Architecture Map` làm bảng truy vết.

**Từ chối:** năm nhân cách agent; trình tạo skill (skill-builder); PRD/PRFAQ/product-brief/sprint-planning/party-mode; các manifest TOML theo từng skill và tầng phân giải cấu hình bằng Python; bất kỳ thứ gì có dung lượng 2.4 MB; các con trỏ văn bản tự do `knowledge` làm cơ chế định tuyến.

**Chỉnh sửa:** tệp spine được chia thành nhiều tệp nhỏ có kiểu dữ liệu rõ ràng thay vì một tài liệu cồng kềnh với 8 phần, bởi vì các phần khác nhau có các nguồn chân lý khác nhau và nhịp độ cập nhật khác nhau, việc trộn lẫn chúng trong một tệp khiến câu hỏi "phần nào bị lỗi thời" trở nên không thể trả lời được theo từng tệp. Linter trở thành một phần của kernel.

---

## 6. OpenSpec

### 6.1 Các dữ kiện thực tế

**DỮ KIỆN.** Cấu trúc: `openspec/specs/<capability-path>/spec.md` (vĩnh viễn), `openspec/changes/<name>/` (đang thực hiện), `openspec/changes/archive/YYYY-MM-DD-<name>/` (đã hoàn thành). Cũng hiện diện trong chính repository này: `openspec/config.yaml`, `openspec/initiatives/`, `openspec/explorations/`.

**DỮ KIỆN.** Các tệp theo từng change: `proposal.md`, `specs/<capability-path>/spec.md` (delta), `design.md`, `tasks.md`, cộng với `.openspec.yaml` mang `schema: spec-driven` và `created: <date>` (và tùy chọn `skip_specs: true`).

**DỮ KIỆN — cơ chế xuất sắc nhất trong tài liệu tham chiếu.** Workflow là một **DAG artifact được khai báo**, không phải một danh sách phase được hardcode. Tệp `schemas/spec-driven/schema.yaml`:

```yaml
name: spec-driven
version: 1
description: Default OpenSpec workflow - proposal → specs → design → tasks
artifacts:
  - id: proposal
    generates: proposal.md
    template: proposal.md
    instruction: |...|
    requires: []
  - id: specs
    generates: "specs/**/*.md"
    template: spec.md
    requires: [proposal]
  - id: design
    generates: design.md
    requires: [proposal]
  - id: tasks
    generates: tasks.md
    requires: [specs, design]
apply:
  requires: [tasks]
  tracks: tasks.md
  instruction: |...|
```

Mỗi artifact mang `id`, `generates` (đường dẫn tương đối hoặc glob), `description`, `template`, một đoạn `instruction` dài (prompt), và `requires` (các cạnh phụ thuộc).

**DỮ KIỆN.** Đồ thị DAG được xác thực một cách xác định trong `src/core/artifact-graph/schema.ts`: phân tích cú pháp Zod schema, sau đó chạy `validateNoDuplicateIds`, `validateRequiresReferences`, `validateNoCycles` (thuật toán DFS báo cáo toàn bộ đường dẫn chu trình). `src/core/artifact-graph/types.ts` từ chối các đường dẫn tuyệt đối, ký tự thoát `..` và byte NUL trong mọi trường đường dẫn.

**DỮ KIỆN.** Trạng thái workflow được **phái sinh từ hệ thống tệp**, không được lưu trữ. `src/core/artifact-graph/state.ts`: hàm `detectCompleted(graph, changeDir)` trả về tập hợp các id artifact có đường dẫn (hoặc glob) trong `generates` tồn tại trên đĩa. Không có tệp trạng thái nào để mà bị hỏng hoặc mất đồng bộ.

**DỮ KIỆN.** Định dạng spec được thực thi nghiêm ngặt. Từ chỉ dẫn `specs` của schema: các requirement là `### Requirement: <name>`, các scenario là `#### Scenario: <name>` với các gạch đầu dòng WHEN/THEN, "**CRITICAL**: Các Scenario BẮT BUỘC phải dùng chính xác 4 dấu thăng (`####`). Dùng 3 dấu thăng hoặc gạch đầu dòng sẽ âm thầm thất bại", "Mọi requirement BẮT BUỘC phải có ít nhất một scenario", "Dùng SHALL/MUST cho các yêu cầu quy chuẩn (tránh should/may)".

**DỮ KIỆN.** Các thao tác delta là một tập hợp đóng gồm các tiêu đề `##`: `ADDED Requirements`, `MODIFIED Requirements` ("BẮT BUỘC phải bao gồm toàn bộ nội dung cập nhật"), `REMOVED Requirements` ("BẮT BUỘC phải bao gồm **Reason** và **Migration**"), `RENAMED Requirements` (FROM:/TO:). Các capability mới phải mở đầu bằng một mục `## Purpose` có độ dài ít nhất `MIN_PURPOSE_LENGTH` ký tự; lệnh `openspec validate --strict` sẽ báo lỗi nếu quá ngắn. Các delta cho capability hiện có **không được** chứa `## Purpose`.

**DỮ KIỆN.** Lệnh `openspec validate` là code thực tế, không phải một prompt: `src/core/validation/validator.ts` + `src/core/parsers/{markdown-parser, change-parser, requirement-blocks, requirement-text, spec-structure, code-fence}.ts` + `src/core/schemas/{spec,change,base}.schema.ts` (Zod) + `validation/{task-numbering, purpose-placeholder, constants}.ts`. Các issue có kiểu rõ ràng `{level: 'ERROR'|'WARNING'|'INFO', path, message, line?, column?}` kèm tổng số đếm. Hàm `findTaskNumberingIssues` phát hiện các id task bị mơ hồ hoặc trùng lặp bên trong các nhóm `## N.`.

**DỮ KIỆN.** Một change có zero spec deltas sẽ bị **từ chối** bởi `openspec validate` trừ khi `.openspec.yaml` đặt `skip_specs: true`, và chỉ dẫn nêu thêm: "Chỉ dùng `skip_specs: true` khi không có hành vi nào ở cấp độ spec bị thay đổi (tái cấu trúc thuần túy, công cụ, tài liệu) … Tuyệt đối không tự bịa ra một requirement chỉ để làm vừa lòng validator."

**DỮ KIỆN — cơ chế đồng bộ tri thức.** `src/core/specs-apply.ts` + `src/core/archive.ts` thực hiện một **thao tác hợp nhất văn bản mang tính xác định** của các khối delta requirement vào các spec capability vĩnh viễn tại thời điểm archive (`findSpecUpdates`, `buildUpdatedSpec`, `foldRequirementName`, `normalizeRequirementName`, `extractRequirementsSection`, `findMissingCurrentScenarios`, `findMainSpecStructureIssues`), kèm theo các assertion kiểm tra bao hàm đường dẫn (`isLexicallyWithin`, `assertPathWithin`) và xác thực trước khi ghi của spec được dựng lại (`validateSpecContent`).

**DỮ KIỆN.** File `openspec/config.yaml` mang theo một khối văn bản tự do `context:` cấp dự án và một bản đồ `rules:` theo từng artifact:

```yaml
schema: spec-driven
context: |
  Tech stack: TypeScript, Node.js (>=20.19.0), ESM modules
  ...
rules:
  specs:
    - Include scenarios for Windows path handling when dealing with file paths
    - Prefer user-facing product behavior and observable outcomes over internal implementation mechanics
  tasks:
    - Add Windows CI verification as a task when changes involve file paths
  design:
    - Prefer Node.js path module over string manipulation for paths
```

**DỮ KIỆN.** Các slash command: `/opsx:explore`, `/opsx:propose`, `/opsx:apply`, `/opsx:archive`, cộng với các workflow cho `update`, `continue`, `ff`, `verify`, `sync-specs`, `bulk-archive`, `onboard`, `feedback`. CLI: `openspec init|update|config|list|list --specs|show|status|instructions|validate|archive|doctor`. Lệnh `openspec instructions apply --change <name> --json` trả về `contextFiles` (id artifact → các đường dẫn tệp cụ thể), đó là cách một skill biết nó cần phải đọc những gì.

**DỮ KIỆN.** Skill `openspec-verify-change` là một prompt. Ba chiều đánh giá của nó là Tính trọn vẹn / Tính đúng đắn / Tính mạch lạc, các mức độ CRITICAL / WARNING / SUGGESTION. Tính trọn vẹn bao gồm các kiểm tra gần như xác định (phân tích `- [ ]` so với `- [x]`, đếm số lượng) nhưng độ bao phủ spec lại là "tìm kiếm codebase các từ khóa liên quan đến requirement… đánh giá xem việc triển khai có khả năng tồn tại hay không".

### 6.2 Cách diễn giải

**CÁCH DIỄN GIẢI.** OpenSpec là *nền tảng* vững chắc nhất trong số sáu dự án, và lý do mang tính kiến trúc chứ không phải phong cách: nó tách biệt rõ ràng **các spec năng lực vĩnh viễn** khỏi **các delta thay đổi tạm thời**, và nó hội tụ chúng bằng mã nguồn, không phải bằng prompt. Thư mục `specs/NNN-feature/` của Spec Kit không bao giờ hội tụ — sau 20 tính năng bạn có 20 thư mục mô tả 20 khoảnh khắc lịch sử và không có gì mô tả toàn thể hệ thống. Thư mục `openspec/specs/` của OpenSpec mô tả hệ thống, và mỗi change là một bản diff đối chiếu với nó, sau đó được gập lại và lưu trữ.

**CÁCH DIỄN GIẢI.** Đồ thị DAG artifact trong `schema.yaml` là cách thức đúng đắn để biến vòng đời thành **thực thi cưỡng chế thay vì gợi ý**, vốn là yêu cầu cốt lõi của đề bài. Hãy chú ý chính xác tại sao nó hoạt động hiệu quả:

- **thứ tự** là dữ liệu (`requires`), vì vậy một script có thể tính toán xem cái gì đang bị chặn;
- **trạng thái** là hệ thống tệp (`generates` tồn tại), vì vậy không có gì để bị mất đồng bộ;
- **prompt** được gắn trực tiếp vào node (`instruction`), vì vậy mô hình nhận được chính xác chỉ dẫn cho bước nó đang đứng và không nhận thứ gì thừa thãi — đây là kỹ nghệ ngữ cảnh như một hệ quả tự nhiên của mô hình dữ liệu;
- **template** được gắn trực tiếp vào node, vì vậy hình thái đầu ra có thể dự đoán được để kiểm định.

Đó là 4 lợi ích khác nhau từ một tệp YAML chỉ vỏn vẹn 40 dòng. Không có thứ gì khác trong tài liệu tham chiếu đạt được hiệu suất này.

**CÁCH DIỄN GIẢI.** Việc từ chối zero-delta kèm lối thoát hiểm `skip_specs: true` có nêu tên là khuôn mẫu đúng đắn cho mọi quy tắc "bạn bắt buộc phải ghi tài liệu điều này" trong một harness: *làm cho sự bỏ qua trở nên tường minh, có tên, và được ghi nhận trong repository, thay vì rơi vào tình trạng không được thực thi hoặc không thể miễn trừ.* Điều này có thể tổng quát hóa trực tiếp cho các yêu cầu ADR và các quyền miễn trừ độ lệch.

**CÁCH DIỄN GIẢI.** Điểm yếu của OpenSpec là tri thức vĩnh viễn của nó chỉ là các yêu cầu *hành vi*. Không có gì về component, ranh giới, hướng phụ thuộc, các invariant không quan sát được từ bên ngoài, mô hình dữ liệu, triển khai, hoặc lý do *tại sao*. Tệp `design.md` nắm giữ các quyết định và lý do lập luận nhưng nó là một artifact theo từng thay đổi và sẽ bị lưu trữ lại — do đó lý do cho một quyết định kiến trúc đang sống cuối cùng lại bị chôn vùi trong `changes/archive/2026-01-06-.../design.md`. Đó chính xác là bài toán ADR chưa được giải quyết.

**CÁCH DIỄN GIẢI.** Bản đồ `rules:` theo từng artifact trong `config.yaml` là một cơ chế chi phí thấp nhưng giá trị cao. Nó cho phép một dự án bơm các ràng buộc thường trực của riêng mình vào việc tạo ra một loại artifact cụ thể mà không cần chỉnh sửa bất kỳ skill nào. Đây cũng là nơi mà "hiến chương" của chúng ta có thể trở thành hoạt động thực thi cụ thể thay vì chỉ là nguyện vọng.

### 6.3 Tiếp thu / Từ chối

**Tiếp thu:** mô hình lấy thay đổi làm trung tâm; spec vĩnh viễn đối chiếu với change delta đối chiếu với archive; lược đồ DAG artifact trong `schema.yaml` (id/generates/requires/template/instruction + `apply.tracks`); trạng thái phái sinh từ hệ thống tệp; xác thực cấu trúc xác định với các issue có kiểu ERROR/WARNING/INFO; tập hợp đóng các thao tác delta kèm Reason/Migration bắt buộc khi xóa; kỷ luật tiêu đề requirement/scenario; quy tắc `MODIFIED phải bao gồm toàn bộ nội dung cập nhật`; gập lưu trữ xác định đóng vai trò cơ chế đồng bộ tri thức; từ chối zero-delta bằng cơ chế bỏ qua có nêu tên và ghi nhận; bơm `rules:` theo từng artifact; lệnh `instructions --json` trả về chính xác các tệp mà một phase được phép đọc; kiểm tra bao hàm đường dẫn an toàn trên mọi đường dẫn được sinh ra.

**Từ chối:** coi requirements là tri thức vĩnh viễn *duy nhất*; đặt lý do lập luận trong các tài liệu thiết kế bị lưu trữ; `openspec-verify-change` dưới dạng một prompt; các tầng initiatives/explorations/workset/store (phình to phạm vi vượt quá nhu cầu của một lập trình viên cá nhân); CLI viết bằng Node/TypeScript làm con đường triển khai duy nhất (không liên quan đến ý tưởng; liên quan đến ngân sách dependency của chúng ta).

**Chỉnh sửa:** mở rộng tầng vĩnh viễn từ "các spec năng lực" thành "các spec năng lực **cộng với** các claim tri thức hệ thống có kiểu **cộng với** các ADR", và làm cho cơ chế gập lưu trữ áp dụng cho cả ba, được điều khiển bởi một bản ghi tác động (impact record) tường minh thay vì suy diễn tự động.

---

## 7. SWE-agent và mini-SWE-agent

### 7.1 Các dữ kiện thực tế

**DỮ KIỆN.** Đóng góp nghiên cứu được tuyên bố của SWE-agent là **Agent-Computer Interface (ACI)** — bài báo được trích dẫn trong repo là "SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering" (NeurIPS 2024). Các công cụ là các gói nằm dưới `tools/`: `windowed`, `windowed_edit_linting`, `windowed_edit_replace`, `windowed_edit_rewrite`, `edit_anthropic`, `search`, `filemap`, `diff_state`, `submit`, `review_on_submit_m`, `forfeit`, `registry`, `web_browser`, `image_tools`.

**DỮ KIỆN — một rào chắn cụ thể rất đáng để sao chép.** Công cụ `tools/windowed_edit_linting` chạy `flake8` **trước** khi sửa, áp dụng việc sửa đổi, chạy `flake8` **sau** khi sửa, tính toán diff giữa hai tập hợp lỗi, và nếu xuất hiện lỗi cú pháp mới, nó **revert việc chỉnh sửa** và trả về `_LINT_ERROR_TEMPLATE`: "Chỉnh sửa đề xuất của bạn đã đưa vào lỗi cú pháp mới. Vui lòng đọc kỹ thông điệp lỗi này và thử chỉnh sửa lại tệp."

**DỮ KIỆN.** `sweagent/agent/reviewer.py` triển khai một vòng lặp thử lại cộng với cơ chế chọn phương án tốt nhất (best-of-n) (`ReviewSubmission` mang toàn bộ quỹ đạo qua các lần thử lại, số liệu thống kê mô hình, và thông tin chi tiết).

**DỮ KIỆN.** Toàn bộ agent của mini-SWE-agent nằm trong `src/minisweagent/agents/default.py`, chỉ khoảng ~200 dòng. Vòng lặp của nó: render `system_template` và `instance_template` thành hai tin nhắn, sau đó `while True: step()`, trong đó `step()` = `execute_actions(query())`. `query()` gọi mô hình; `execute_actions()` chạy từng hành động đã phân tích cú pháp qua `self.env.execute(action)` và nối thêm phần quan sát thu được. Điều kiện dừng là `messages[-1]['role'] == 'exit'`.

**DỮ KIỆN.** Các giới hạn ngân sách cứng được thực thi bằng mã nguồn, không phải qua prompt: `step_limit`, `cost_limit` (mặc định 3.0), `wall_time_limit_seconds`, `max_consecutive_format_errors` (mặc định 3). Vượt quá bất kỳ giới hạn nào sẽ raise `LimitsExceeded` / `TimeExceeded` / `RepeatedFormatError`, vốn sẽ thêm một tin nhắn `exit`. Thao tác `save(self.config.output_path)` chạy trong một khối `finally` ở **mọi** bước, do đó toàn bộ quỹ đạo liên tục được lưu trên đĩa.

**DỮ KIỆN.** Giao diện của nó được chủ ý tinh giản tối đa: `default.yaml` yêu cầu "chính xác MỘT khối code bash với MỘT lệnh (hoặc các lệnh nối nhau bằng && hoặc ||)", một phần THOUGHT đứng trước, và lưu ý "Các thay đổi thư mục hoặc biến môi trường không được duy trì. Mọi hành động đều được thực thi trong một subshell mới." Quy trình được khuyến nghị của nó, trích nguyên văn từ `instance_template`: "1. Phân tích codebase bằng cách tìm và đọc các tệp liên quan 2. Tạo một script để tái hiện vấn đề 3. Chỉnh sửa mã nguồn để giải quyết vấn đề 4. Xác minh bản sửa lỗi của bạn bằng cách chạy lại script 5. Kiểm thử các trường hợp biên để đảm bảo bản sửa lỗi là vững chắc 6. Submit các thay đổi của bạn …". Tín hiệu hoàn thành là một lệnh echo đặc biệt: `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`.

**DỮ KIỆN.** README tuyên bố: "Chỉ khoảng 100 dòng python cho class agent"; "Đạt điểm >74% trên benchmark SWE-bench verified"; "khởi động nhanh hơn nhiều so với Claude Code"; "mini-swe-agent hiện đang vận hành Ramp SWE-Bench". Đây là các tuyên bố của chính dự án; tôi không độc lập tái lập lại benchmark này.

### 7.2 Cách diễn giải

**CÁCH DIỄN GIẢI.** Cặp đôi này là một thí nghiệm có đối chứng về việc một vòng lặp thực thi thực sự cần bao nhiêu giàn giáo bao quanh, và câu trả lời là "rất ít, nếu môi trường là trung thực". Phiên bản ~200 dòng của mini chỉ dùng `bash` đã đạt kết quả chỉ kém vài điểm so với phiên bản được xây dựng công phu phức tạp. Đó là một lập luận đanh thép chống lại việc tự xây dựng một execution engine riêng.

**CÁCH DIỄN GIẢI.** Những gì mini có mà prompt không thể mang lại, và là những thứ chúng ta nên sao chép: **ngân sách được thực thi bằng mã nguồn, và quỹ đạo được lưu vết liên tục ở mỗi bước**. Một giới hạn về số bước/chi phí/thời gian biến việc "agent chạy lung tung mất kiểm soát trong 2 tiếng" từ một vấn đề giám sát con người thành một thất bại có giới hạn kèm log rõ ràng. Đây là cơ chế đảm bảo độ tin cậy ít tốn kém nhất trong toàn bộ tài liệu tham chiếu.

**CÁCH DIỄN GIẢI.** `windowed_edit_linting` là khuôn mẫu chuẩn xác cho kiểu thực thi đúng đắn: rào chắn nằm *bên trong công cụ*, mang tính xác định, và thông điệp thất bại của nó dạy cho mô hình biết phải làm gì tiếp theo. So sánh với cách tiếp cận của Superpowers cho cùng lớp vấn đề (một chỉ dẫn in hoa bảo đừng làm hỏng code). Phiên bản ở cấp độ công cụ không thể bị lách luật bằng lý lẽ bao biện.

**CÁCH DIỄN GIẢI.** Cả hai dự án đều mang định dạng phục vụ benchmark: nhận một issue, xuất ra một bản vá. Chúng không có đặc tả, không có kiến trúc, không lưu trữ giữa các tác vụ, và hoàn toàn không có khái niệm về tri thức hệ thống. Chúng thuộc về phạm vi bên trong phase `implement` và `debug` của chúng ta và tuyệt đối không nằm ở đâu khác.

**CÁCH DIỄN GIẢI.** Quy trình khuyến nghị của mini *chính là* kỷ luật ưu tiên tái hiện lỗi trước, và nó hoàn toàn đồng thuận với `systematic-debugging` của Superpowers ("KHÔNG SỬA LỖI NẾU CHƯA ĐIỀU TRA NGUYÊN NHÂN GỐC RỄ"). Hai dự án độc lập cùng hội tụ về "tái hiện lỗi trước khi sửa" là tín hiệu phương pháp luận mạnh mẽ nhất trong tài liệu tham chiếu.

### 7.3 Tiếp thu / Từ chối

**Tiếp thu:** ngân sách cứng bằng mã nguồn (số bước, chi phí, thời gian thực, số lỗi định dạng liên tiếp); lưu vết quỹ đạo liên tục ở mọi bước; tái hiện trước khi sửa; vòng lặp quan sát → hành động với một hành động cho mỗi bước cho vòng lặp triển khai bên trong; rào chắn được triển khai trong công cụ kèm thông điệp lỗi mang tính hướng dẫn (diff linter trước/sau → revert); cơ chế best-of-n với một reviewer rõ ràng, chỉ dành cho các tác vụ quan trọng cao.

**Từ chối:** tự xây dựng một execution engine riêng, lớp trừu tượng môi trường, hoặc client gọi mô hình — host agent (Claude Code và các công cụ tương đương) đã cung cấp sẵn những thứ này; 15 gói công cụ tùy biến của SWE-agent; hệ thống đường ống phục vụ benchmark.

**Chỉnh sửa:** vòng lặp bên trong vẫn thuộc về host agent; chúng ta chỉ đóng góp *hợp đồng đầu vào* (task là gì, tệp nào được phép chạm, test nào bắt buộc phải chuyển sang màu xanh) và *hợp đồng đầu ra* (bằng chứng).

---

## 8. GSD / GSD Core

### 8.1 Các dữ kiện thực tế

**DỮ KIỆN.** Quy mô. Bản lưu trữ `get-shit-done` có ~90 tệp workflow và ~68 slash command. `gsd-core` có 44 gói capability dưới `capabilities/`.

**DỮ KIỆN — vật tương tự hiện có gần nhất với tầng Tri thức Hệ thống trong đề bài.** Thư mục `get-shit-done/templates/codebase/` định nghĩa bảy tài liệu được ghi vào `.planning/codebase/`:
`STACK.md` (ngôn ngữ, runtime, trình quản lý gói, framework, testing, build),
`STRUCTURE.md` (cây cấu trúc thư mục, mục đích thư mục, vị trí tệp chính, điểm nhập),
`ARCHITECTURE.md` (tổng quan mẫu thiết kế, các tầng khái niệm kèm Mục đích/Chứa/Phụ thuộc vào/Được dùng bởi, luồng dữ liệu), `CONVENTIONS.md` (đặt tên, định dạng, phong cách), `INTEGRATIONS.md` (API bên ngoài, auth, lưu trữ dữ liệu, giới hạn tốc độ rate limit), `TESTING.md` (runner, thư viện assertion, lệnh chạy, tổ chức tệp), `CONCERNS.md` (nợ kỹ thuật kèm Vấn đề/Tại sao/Tác động/Hướng xử lý, bug đã biết kèm Triệu chứng/Kích hoạt/Cách khắc phục tạm/Nguyên nhân gốc rễ, các lưu ý bảo mật). Mọi tiêu đề template đều mang dòng `**Analysis Date:** [YYYY-MM-DD]`.

**DỮ KIỆN.** Chúng được tạo ra bởi `map-codebase.md` (443 dòng), vốn rẽ nhánh song song các subagent `gsd-codebase-mapper`, mỗi subagent tự ghi trực tiếp tài liệu của riêng mình. Lý do được nêu: "Ngữ cảnh tươi mới cho mỗi domain (không làm ô nhiễm token) / các agent ghi tài liệu trực tiếp (không chuyển ngữ cảnh ngược lại bộ điều phối) / bộ điều phối chỉ tóm tắt lại những gì đã được tạo (sử dụng ngữ cảnh tối thiểu)". Nó hỗ trợ lập lại bản đồ gia tăng `--paths p1,p2`, xác thực các đối số đường dẫn chống lại `..`, dấu gạch chéo `/` ở đầu và các ký tự đặc biệt của shell, và đóng dấu `last_mapped_commit: <HEAD sha>` vào YAML frontmatter của mỗi tài liệu.

**DỮ KIỆN — các cổng phát hiện độ lệch.** Tệp `capabilities/drift/capability.json` khai báo bốn cổng:

| point | check | blocking | when |
|---|---|---|---|
| `execute:wave:post` | `verify.schema-drift` | **true** | `workflow.schema_drift_gate` |
| `execute:wave:post` | `verify.codebase-drift` | false | `workflow.schema_drift_gate` |
| `plan:pre` | `verify.codebase-drift` | false | `workflow.plan_drift_precheck` |
| `plan:pre` | `verify.context-drift` | false | `workflow.context_drift_precheck` |

Cả bốn cổng đều mang `onError: skip`. Cấu hình: `workflow.drift_threshold` (mặc định 3), `workflow.drift_action` (`warn` | `auto-remap`, mặc định `warn`), cộng với các giá trị boolean theo từng cổng và `workflow.context_drift_action` (`warn` | `block`).

Cổng schema được mô tả là: "chặn việc xác minh nếu các tệp liên quan đến schema bị thay đổi trong quá trình thực thi nhưng không có lệnh push database nào được chạy" — lý do là để "ngăn chặn việc xác minh dương tính giả nơi mà build/types đều pass vì các kiểu TypeScript đến từ config chứ không phải từ database thực tế" (`capabilities/schema-gate`).

Cổng **context-drift** được mô tả là: "So sánh thời gian thay đổi cuối có hiệu lực của từng artifact (thời gian commit git, lùi về mtime đối với các chỉnh sửa chưa commit) đối chiếu với thời gian của chính CONTEXT.md — một artifact cũ hơn quyết định mới nhất của CONTEXT.md được xem là phái sinh từ một tiền đề đã bị thay đổi."

**DỮ KIỆN.** Tệp `gsd-core/CONTEXT.md` mở đầu bằng: "**Định dạng**: tài liệu này có thể grep được bằng máy. Mỗi dữ kiện hoạt động là một vị từ một dòng (`CLASS.subkey=value`). Bản tóm tắt của agent trích dẫn các vị từ theo ID nguyên văn (theo `META.RULE.brief-must-cite-doc`) — tuyệt đối không diễn giải lại từ tệp này. Những điều mới học được đưa vào dưới dạng các vị từ; văn xuôi theo thứ tự thời gian thuộc về nhật ký phiên làm việc ở phía dưới."

**DỮ KIỆN.** Các điểm đặt cổng được sử dụng xuyên suốt toàn bộ các capability: `plan:pre` (14 cổng), `execute:wave:post` (7), `verify:post` (4), `plan:post` (4), `execute:post` (3), `ship:pre` (2), `verify:pre` (1), `ship:post` (1), `execute:wave:pre` (1), `discuss:pre` (1), `discuss:post` (1).

**DỮ KIỆN.** Các capability liên quan khác, trích nguyên văn mô tả của chúng:

- `intel` — "Kho thông tin tình báo code … các lệnh con của `gsd-tools intel` (query, status, update, diff, snapshot, patch-meta, validate, extract-exports, api-surface)". `docs/features/queryable-codebase-intelligence.md` chỉ định các tệp JSON trong `.planning/intel/`: `stack.json`, `api-map.json`, `dependency-graph.json`, `file-roles.json`, `arch-decisions.json`, với "chế độ `status` BẮT BUỘC phải báo cáo độ tươi mới (FRESH/STALE, ngưỡng lỗi thời: 24 giờ)".
- `graphify` — "Xây dựng, truy vấn và kiểm tra đồ thị tri thức dự án trong `.planning/graphs/`", chọn tham gia qua `graphify.enabled`, các lệnh con `build|query|status|diff|snapshot`. Tính lỗi thời dựa trên commit được bổ sung sau: `built_at_commit`, `current_commit`, `commits_behind`, `commit_stale` (nullable), kèm xác thực rằng `built_at_commit` là 4–40 ký tự hex "trước khi chạm tới `git` — một tệp `graph.json` độc hại không thể tiêm các tùy chọn gạch nối vào argv".
- `gap-analysis` — "đối chiếu chéo mọi REQ-ID và D-ID từ REQUIREMENTS.md và CONTEXT.md đối chiếu với phần thân kế hoạch. Xuất ra một bảng Nguồn | Mục | Trạng thái. Không chặn việc chuyển phase."
- `broken-windows` — "Sổ đăng ký khiếm khuyết xuyên phase tích lũy các stub, TODO, test bị skip, các lần xác minh chưa chạy, và các sự thật chưa thỏa mãn vào .planning/WINDOWS.md. Khi việc thực thi được bật, nó chặn lệnh /gsd-ship khi có bất kỳ ô cửa sổ nào đang mở trừ khi được miễn trừ rõ ràng kèm lý do được ghi nhận."
- `nyquist` — "Đợt kiểm toán độ bao phủ xác thực ánh xạ công việc đã thực thi ngược lại các bài test và bằng chứng thuần thủ công."
- `refactor-trigger` — đo lường độ phức tạp của code bị chạm tới, đề xuất một đợt tái cấu trúc có phạm vi khi một hàm "vượt qua một ngưỡng đã cấu hình hoặc nhảy vọt qua mốc neo được ghi nhận của nó"; "Mặc định mang tính tư vấn — nó không bao giờ sửa code và không bao giờ chặn."
- `assumption-delta` — "kích hoạt khi một phase biến một thứ thành số nhiều, tùy chọn, hoặc được lựa chọn trong khi trước đây nó là số ít, bắt buộc, hoặc phái sinh. Làm nổi lên một câu hỏi về mô hình định danh … để một độ lệch khóa chính âm thầm không tích tụ thành một lỗi người dùng sau này. Không chặn; chỉ kích hoạt khi phát hiện tín hiệu."
- `tdd` — "Bơm các heuristic TDD vào bộ lập kế hoạch và thực thi việc tuân thủ cổng RED/GREEN trên các kế hoạch type:tdd sau khi thực thi."

**DỮ KIỆN.** Thư mục `get-shit-done/get-shit-done/contexts/` chứa chính xác ba tệp ngữ cảnh: `dev.md`, `research.md`, `review.md`.

### 8.2 Cách diễn giải

**CÁCH DIỄN GIẢI.** GSD là dự án tiên tiến nhất về mặt *cơ học* trong sáu dự án và cũng là dự án bị xây dựng thừa thãi nhất. Mô hình cổng khai báo của nó — một điểm vòng đời có tên, một kiểm tra được định danh bằng một chuỗi truy vấn, một cờ `blocking`, một vị từ cấu hình `when`, và `onError: skip` — là kiến trúc chuẩn xác để biến một vòng đời thành có thể thực thi cưỡng chế, và toàn bộ engine đó chỉ khoảng 100 dòng code. Mọi thứ có giá trị trong câu chuyện phát hiện độ lệch của GSD đều là hạ nguồn của sự trừu tượng duy nhất đó.

**CÁCH DIỄN GIẢI.** Ba cổng phát hiện độ lệch tạo thành một phân loại học mà bản tóm lược nhiệm vụ chưa có, và nó là một phân loại tốt hơn nhiều so với cụm từ "độ lệch kiến trúc":

1. **Độ lệch cấu trúc (Structural drift)** — code mọc thêm một hình thái mà bản đồ không nhắc tới. Rẻ, mang tính xác định, recall cao, precision thấp. Câu trả lời đúng: lập lại bản đồ, không chặn.
2. **Độ lệch quy trình (Process drift)** — một loại thay đổi diễn ra mà thiếu hành động bắt buộc đi kèm (tệp schema bị sửa mà không có lệnh push migration). Xác định, precision cao. Câu trả lời đúng: **chặn (block)**.
3. **Độ lệch tiền đề (Premise drift)** — một artifact phái sinh cũ hơn quyết định mà nó được phái sinh từ đó. Xác định, rẻ, và nó bắt được dạng thất bại quan trọng nhất đối với các agent: lập kế hoạch dựa trên các phân tích đã lỗi thời.

**CÁCH DIỄN GIẢI — thủ thuật đơn lẻ có thể tái sử dụng tốt nhất trong GSD.** Độ lệch tiền đề bằng cách so sánh dấu thời gian (`artifact.mtime < CONTEXT.md.newest_decision`) hoàn toàn không tốn chi phí và trả lời câu hỏi "liệu phân tích này có còn đáng tin cậy không?" mà không cần bất kỳ ngữ nghĩa nào. Hãy tổng quát hóa nó: **mỗi artifact phái sinh đều ghi nhận những gì nó được phái sinh từ đó; tính lỗi thời là một phép so sánh, không phải một phán đoán.**

**CÁCH DIỄN GIẢI.** Quy tắc "vị từ một dòng, được trích dẫn theo ID nguyên văn, không bao giờ diễn giải lại" của `CONTEXT.md` là câu trả lời ở cấp độ định dạng cho bài toán chống nhiễu. Một vị từ là ngắn gọn, có thể định địa chỉ, có thể grep được, và có thể diff được; một đoạn văn xuôi thì không có đặc tính nào trong số đó. Điều cấm diễn giải lại là thứ giúp khả năng truy vết tồn tại lâu dài: nếu các bản tóm tắt trích dẫn `AUTH.session.ttl=30m` theo id, một lệnh grep cho bạn biết mọi nơi mà dữ kiện đó đang giữ vai trò trụ cột.

**CÁCH DIỄN GIẢI.** `broken-windows` là một ý tưởng thực sự xuất sắc nhưng bị đặt tên chưa chuẩn. Một sổ đăng ký mang tính chặn ghi lại "những thứ chúng ta cố tình để dở dang, mỗi mục hoặc được sửa hoặc được miễn trừ tường minh kèm lý do" chính là cách bạn ngăn chặn một agent tuyên bố hoàn thành trên một đống `TODO` và `it.skip`. Đây là phiên bản có thể thực thi cưỡng chế của nguyên tắc "harness không được phép tuyên bố thành công chỉ vì tests pass".

**CÁCH DIỄN GIẢI.** Nơi GSD đi chệch hướng: 44 capabilities, ~90 workflows, một đồ thị tri thức, một kho thông tin tình báo, một tích hợp MCP kiểu cung điện ký ức, và 14 cổng kiểm soát chỉ riêng tại `plan:pre`. Quy tắc tươi mới của `intel` ("ngưỡng lỗi thời: 24 giờ") là một heuristic dựa trên thời gian trong khi hoàn toàn có thể dùng commit — và quả thực `graphify` sau đó đã bổ sung chính xác điều đó (`built_at_commit`, `commits_behind`), điều này được xem như một sự thừa nhận nội bộ rằng phiên bản dựa trên thời gian là sai lầm. **Hai kho tri thức (JSON của `.planning/intel/` và đồ thị của `.planning/graphs/`) cộng với bảy bản đồ markdown cộng với các vị từ trong `CONTEXT.md` đồng nghĩa với việc có tới bốn cách biểu diễn khác nhau cho cùng một hệ thống, mỗi thứ có một câu chuyện lỗi thời riêng.** Đó chính là hình thái thất bại mà harness của chúng ta bắt buộc phải né tránh ngay từ thiết kế.

### 8.3 Tiếp thu / Từ chối

**Tiếp thu:** mô hình cổng khai báo (point + check + `blocking` + `when` + `onError`); phân loại độ lệch 3 hướng (structural / process / premise) và chính sách chặn chuẩn xác cho từng loại (warn / block / warn-or-block); xuất xứ `last_mapped_commit` / `built_at_commit` trong frontmatter; tính lỗi thời dựa trên commit thay vì dựa trên thời gian; `commits_behind` như một tín hiệu rõ ràng; các vị từ một dòng có thể grep bằng máy được trích dẫn theo ID và không bao giờ diễn giải lại; một sổ đăng ký khiếm khuyết mang tính chặn kèm các miễn trừ được ghi nhận; đối chiếu chéo độ bao phủ của requirement-ID (`gap-analysis`); các mapper rẽ nhánh song song tự ghi tệp riêng để tránh làm tràn ngữ cảnh; lập lại bản đồ gia tăng `--paths` kèm xác thực đối số; không bao giờ tin tưởng các giá trị lưu trữ truyền tới shell (xác thực hex của `built_at_commit`).

**Từ chối:** 44 capabilities; một đồ thị tri thức; một kho thông tin tình báo JSON thứ hai; tích hợp bộ nhớ MCP; 14 cổng kiểm soát tại một điểm vòng đời duy nhất; các ngưỡng tươi mới dựa trên thời gian; auto-remap làm mặc định (nó âm thầm viết lại bản đồ cho khớp với code — chính xác là hành vi mà đề bài nghiêm cấm); ~90 tệp workflow.

**Chỉnh sửa:** gộp `intel` + `graphify` + bảy bản đồ thành **một** kho phái sinh duy nhất với một quy tắc xuất xứ duy nhất; `auto-remap` trở thành `propose-remap` và tuyệt đối không bao giờ tự ý ghi đè nếu không có phán quyết của con người khi claim bị lệch là một claim trụ cột.

---

## 9. Nghiên cứu mở rộng ngoài 6 dự án

Chỉ những dự án làm thay đổi một quyết định thiết kế mới được liệt kê dưới đây.

### 9.1 Neo tài liệu vào mã nguồn — Thứ gần nhất với một giải pháp hoàn chỉnh

**DỮ KIỆN.** Doc linter `drift` của Fiberplane neo các tệp tài liệu vào mã nguồn thông qua frontmatter hoặc các chú thích nội dòng:

```
---
drift:
  files:
    - src/auth/login.ts@a1b2c3d
    - src/auth/provider.ts#AuthConfig@a1b2c3d
---
```

Một anchor là *đường dẫn* (bắt buộc) + `#Symbol` (tùy chọn, thu hẹp vào một khai báo) + `@<git-sha>` (tùy chọn, "commit nào đã xử lý neo này lần gần nhất"). Phát hiện lỗi thời: lấy baseline commit (từ xuất xứ, nếu không có thì lấy lần sửa đổi cuối của tệp spec), lấy tệp/symbol tại baseline đó bằng `git show`, và so sánh với phiên bản hiện tại. Đối với TypeScript, Python, Rust, Go, Zig và Java, nó "phân tích code bằng tree-sitter và băm một normalized AST fingerprint (node kinds + token text, loại bỏ khoảng trắng và dữ liệu vị trí)"; các ngôn ngữ không hỗ trợ sẽ lùi về so sánh nội dung thô. Hạn chế được nêu rõ: nó "hỗ trợ việc *phát hiện*, không hỗ trợ bản thân việc review" — một người dùng có thể liên kết lại mà không thèm cập nhật phần văn xuôi.
Nguồn: <https://fiberplane.com/blog/drift-documentation-linter/>

**CÁCH DIỄN GIẢI.** Đây chính là cơ chế mà bản tóm lược đang tìm kiếm và không có dự án nào trong số 6 dự án có được. Nó mang lại **khả năng phát hiện lỗi thời mang tính xác định, không phụ thuộc khoảng trắng hay định dạng, được định phạm vi theo từng symbol** kèm xuất xứ theo từng claim, sử dụng các công cụ mà chúng ta đã có sẵn (git + tree-sitter). Nó không cho bạn biết liệu phần văn xuôi có *sai* hay không — không thứ gì có thể làm được điều đó tuyệt đối — nhưng nó cho bạn biết chính xác phần văn xuôi nào *chưa được xác minh tính đến commit này*, đó là nửa phần thông tin có thể hành động được.

**KHUYẾN NGHỊ.** Tiếp thu các neo `path#Symbol@sha` với normalized AST fingerprints làm nguyên thủy phát hiện lỗi thời chính cho tầng Tri thức Hệ thống của chúng ta. Đây là sự nhập khẩu quan trọng nhất từ bên ngoài sáu repository tham chiếu.

### 9.2 Tuân thủ kiến trúc dưới dạng các quy tắc thực thi được

**DỮ KIỆN.** Các công cụ trưởng thành, được sử dụng rộng rãi theo từng hệ sinh thái thực thi các quy tắc về hướng phụ thuộc và ranh giới module dưới dạng tests hoặc kiểm tra CI: **ArchUnit** (Java; "kiểm tra phụ thuộc giữa các package và class, các layer và slice, kiểm tra chu trình phụ thuộc; thư viện quy tắc kiến trúc phân tầng/onion") kèm các bản port cộng đồng **ArchUnitTS** và **ArchUnitPython**; **dependency-cruiser** (JS/TS; các quy tắc phụ thuộc `forbidden`/`allowed` dựa trên rule); **Tach** (Python; "định nghĩa ranh giới và kiểm soát phụ thuộc giữa các package Python của bạn… mỗi package cũng có thể định nghĩa public interface của nó", triển khai bằng Rust); **Deptrac** (PHP; "định nghĩa các tầng kiến trúc trên các class và quy tắc nào áp dụng cho chúng").
Nguồn: <https://www.archunit.org/>, <https://github.com/TNG/ArchUnit>,
<https://github.com/sverweij/dependency-cruiser>, <https://github.com/tach-org/tach>,
<https://github.com/deptrac/deptrac>, <https://github.com/LukasNiessen/ArchUnitTS>.

**DỮ KIỆN.** Có nghiên cứu bình duyệt về đúng vấn đề này: *Detecting deviations in the code using architecture view-based drift analysis*, Computer Standards & Interfaces, 2023, doi:10.1016/j.csi.2023.103774.

**DỮ KIỆN.** **Structurizr DSL** cung cấp kiến trúc dưới dạng mã nguồn (architecture-as-code) cho mô hình C4, với một DSL có thể phân tích cú pháp và kiểm định trong CI. Nguồn: <https://docs.structurizr.com/dsl>.

**CÁCH DIỄN GIẢI.** Đối với một *tập hợp con* các claim kiến trúc — "tầng domain không được import tầng web", "không có chu trình giữa các package", "chỉ `src/repos/` mới được import database client" — việc phát hiện độ lệch là một bài toán đã được giải quyết triệt để, mang tính xác định và có sẵn trong hệ sinh thái. Chưa ai trong sáu dự án kết nối điều này. Các trường `Binds` + `Rule` trong spine của BMAD chỉ cách một bước ngắn để có thể biên dịch thành chính những quy tắc này.

**KHUYẾN NGHỊ.** Bất kỳ claim kiến trúc nào *có thể* biểu diễn thành một quy tắc phụ thuộc thì **bắt buộc** phải biểu diễn như vậy, và harness sẽ lưu đường dẫn tệp quy tắc làm bằng chứng cho claim đó. Các claim không thể cơ giới hóa vẫn được cho phép, nhưng bắt buộc phải được dán nhãn là `asserted` thay vì `enforced`, và harness sẽ báo cáo tỷ lệ này. Điều này biến việc "phát hiện độ lệch kiến trúc" từ một bài toán AI thành một bài toán linting cho phần quan trọng nhất, và làm cho phần chưa cơ giới hóa còn lại trở nên minh bạch thay vì giả vờ rằng nó đã được bao phủ.

### 9.3 Độ lệch giao diện và mô hình dữ liệu

**DỮ KIỆN.** **oasdiff** so sánh hai tài liệu OpenAPI, phân loại từng điểm khác biệt là phá vỡ tương thích (breaking) hoặc không phá vỡ (non-breaking), trả về mã thoát khác 0 khi vượt qua mức độ nghiêm trọng đã chọn đóng vai trò cổng merge, và hỗ trợ OpenAPI 3.0/3.1/3.2. Nguồn: <https://github.com/oasdiff/oasdiff>, <https://www.oasdiff.com/docs/breaking-changes>.
**Pact** cung cấp kiểm thử hợp đồng định hướng bởi consumer (consumer-driven contract testing). **Schemathesis** tự động sinh các bài test dựa trên thuộc tính từ schema OpenAPI/GraphQL và báo cáo các vi phạm response-schema. **Spectral** kiểm tra lint các tài liệu OpenAPI/AsyncAPI đối chiếu với các bộ quy tắc tùy biến.

**CÁCH DIỄN GIẢI.** "Thay đổi API mà không cập nhật hợp đồng" — mục 6 trong danh sách kiểm tra phân tích của đề bài — hoàn toàn mang tính xác định khi và chỉ khi hợp đồng được sinh ra từ code (hoặc code được sinh ra từ hợp đồng). Phép kiểm tra là chạy `oasdiff` giữa hợp đồng đã commit và hợp đồng được tạo lại tại HEAD, kèm một cổng kiểm soát mức độ nghiêm trọng. Hình thái tương tự cho mô hình dữ liệu: diff snapshot của ORM/schema, hoặc bắt buộc phải có một tệp migration. Cổng schema mang tính chặn của GSD là phiên bản thô sơ của điều này, và nó mang tính chặn vì lý do hoàn toàn chính đáng.

### 9.4 Ngữ cảnh codebase cho Agent: Những gì thực sự cần thiết

**DỮ KIỆN.** **Repo map của Aider** phân tích cú pháp từng tệp bằng tree-sitter để trích xuất các symbol được định nghĩa, xây dựng một đồ thị trong đó các tệp là node và các tham chiếu symbol là cạnh, và xếp hạng bằng thuật toán **PageRank cá nhân hóa** thiên vị các symbol xuất hiện trong đoạn chat hiện tại, tuần tự hóa các symbol có thứ hạng cao nhất vào một bản đồ nhỏ gọn nằm trong ngân sách token (`--map-tokens`, mặc định 1k). Nguồn: <https://aider.chat/2023/10/22/repomap.html>.

**DỮ KIỆN.** Điều hướng code chính xác ở quy mô lớn sử dụng **SCIP** (bản kế nhiệm dựa trên Protobuf của Sourcegraph cho LSIF; tuyên bố "nhỏ hơn 8 lần, và có thể xử lý nhanh hơn 3 lần" so với LSIF, và được tích hợp với **Glean** của Meta chỉ trong ~550 dòng so với 1.500 dòng của LSIF). Nguồn: <https://sourcegraph.com/blog/announcing-scip>.

**DỮ KIỆN.** Quy ước của OpenHands: `AGENTS.md` tại thư mục gốc repo cho "các quy ước ngắn gọn trên toàn bộ repository", `SKILL.md` cho "tri thức tập trung chỉ cần cho một số tác vụ", `.openhands/microagents/repo.md` như một bản tổng quan cấp cao luôn được nạp liên kết tới `.openhands/memory/` để lấy chi tiết; và một giao thức cập nhật trong đó agent "luôn phải hỏi sự xác nhận của người dùng trước bằng cách liệt kê chính xác các mục dự định lưu … và chỉ lưu những mục mà người dùng phê duyệt."
Nguồn: <https://github.com/OpenHands/OpenHands/blob/main/AGENTS.md>, <https://docs.openhands.dev/overview/skills>.

**DỮ KIỆN.** AWS **Kiro** cung cấp bộ ba tương tự Spec Kit dưới các tên gọi khác — `requirements.md`, `design.md`, `tasks.md` — cộng với **các tệp điều hướng (steering files)** (ngữ cảnh dự án bền vững được đọc ở mỗi lần tương tác) và **các hook** (tự động hóa theo sự kiện khi lưu / tạo / commit tệp, ví dụ "xác thực việc hoàn thành task đối chiếu với requirements.md của bạn sau mỗi commit").

**CÁCH DIỄN GIẢI.** Ba kết luận độc lập:

1. **Ngữ cảnh cấu trúc ở cấp độ symbol là rẻ và hiệu quả, và chúng ta không nên tự xây dựng nó.** Aider, Sourcegraph, và tính năng tìm kiếm của chính host agent đều đã giải quyết bài toán này. Harness của chúng ta nên *khám phá* cấu trúc tại thời điểm truy vấn (grep, tree-sitter, các công cụ của host) và chỉ lưu trữ những gì mà việc khám phá không thể trích xuất lại được.
2. **Giao thức "hỏi trước khi lưu, liệt kê chính xác các mục" từ OpenHands là thiết lập mặc định đúng đắn cho các thao tác ghi tri thức.** Nó chỉ tốn một lần tương tác và ngăn chặn việc tích tụ dần dần mớ tiếng ồn đầy tự tin.
3. **Các hook của Kiro xác nhận độc lập cho mô hình cổng kiểm soát.** Hai trong số các thiết kế thương mại/OSS mạnh mẽ nhất (hook của Kiro, cổng của GSD) đều đi đến cùng một điểm: các kiểm tra xác định được kích hoạt theo sự kiện bao quanh vòng đời, chứ không phải nhồi nhét thêm prompt vào bên trong nó.

### 9.5 Bằng chứng về Kỹ nghệ ngữ cảnh (Context engineering)

**DỮ KIỆN.** Nghiên cứu "context rot" năm 2025 của Chroma đã thử nghiệm trên 18 mô hình tiên tiến và nhận thấy sự suy giảm chất lượng khi độ dài đầu vào tăng lên ở mọi nấc kiểm thử, từ rất lâu trước khi chạm tới giới hạn cửa sổ ngữ cảnh. Các biện pháp giảm thiểu hiện đã trở thành tiêu chuẩn trong y văn: truy xuất đúng lúc (just-in-time retrieval - giữ các tham chiếu nhẹ, chỉ fetch nội dung khi cần), nén ngữ cảnh (compaction), ghi chú có cấu trúc, và cô lập subagent.

**CÁCH DIỄN GIẢI.** Đây là bằng chứng thực nghiệm củng cố cho sự cô lập phase của GSD, subagent-tươi-mới-cho-mỗi-task của Superpowers, và `instruction`/`contextFiles` theo từng artifact của OpenSpec. Nó cũng là lập luận đanh thép chống lại một tài liệu tri thức hệ thống đồ sộ luôn luôn được nạp: **một tệp `architecture.md` dài 3.000 dòng được nạp vào mọi phiên làm việc sẽ chủ động làm suy giảm năng lực của agent.** Kết luận độc lập của BMAD "mỗi dòng đều phải trả giá trong mọi phiên làm việc, và khả năng tuân thủ chỉ dẫn suy giảm khi tập nạp mở rộng" cũng khẳng định điều tương tự.

**KHUYẾN NGHỊ.** Áp đặt một **ngân sách token cứng cho tri thức nạp-liên-tục** (mục tiêu: tổng cộng ≤400 dòng trên toàn bộ tập nạp-liên-tục) và đặt mọi thứ khác ra sau một trigger có thể quan sát được (một đường dẫn, một loại tệp, một phase có tên). Việc vượt ngân sách bắt buộc phải giải quyết bằng cách cắt giảm hoặc di dời bớt, tuyệt đối không bao giờ nâng ngân sách lên.

### 9.6 Phân tích tác động thay đổi và chọn lọc test

**DỮ KIỆN.** **CodePlan** (Microsoft Research; ACM PACMSE, doi:10.1145/3643757; arXiv:2309.12499) định hình việc lập trình ở cấp độ repository như một bài toán lập kế hoạch: "sự kết hợp mới mẻ giữa phân tích phụ thuộc gia tăng, phân tích thay đổi có thể ảnh hưởng và thuật toán lập kế hoạch thích ứng", tổng hợp một chuỗi các chỉnh sửa trong đó mỗi bước là một lệnh gọi LLM trên một vị trí code kèm ngữ cảnh trích xuất từ repo, lan truyền thay đổi tới code phụ thuộc.

**DỮ KIỆN.** Phân tích tác động kiểm thử (Test impact analysis) đã có sẵn giải pháp đóng gói: **OpenClover** (Java/Groovy, ánh xạ độ bao phủ theo từng bài test và chọn lọc dựa trên thay đổi), **pytest-impact** ("chỉ chọn các bài test bị ảnh hưởng bởi một git diff, không cần truy vết độ bao phủ hay cơ sở dữ liệu"), Datadog Test Impact Analysis (thương mại).

**CÁCH DIỄN GIẢI.** Hình thái thần kinh-biểu tượng (neuro-symbolic) của CodePlan là *ý tưởng* đúng đắn cho phase impact của chúng ta — tính toán bán kính ảnh hưởng ứng viên bằng phân tích tĩnh, sau đó để mô hình lập luận trên đó — nhưng việc tự xây dựng phân tích phụ thuộc gia tăng vượt xa quy mô của một harness cá nhân. Phiên bản khả thi trong thực tế là: chạy công cụ phân tích phụ thuộc/import của hệ sinh thái trên các tệp bị thay đổi để lấy danh sách phụ thuộc ngược, giao cắt với các component được nêu tên trong Tri thức Hệ thống, và trao cho mô hình danh sách đó làm tập tác động *ứng viên* để nó chọn lọc và hoàn thiện.

---

## 10. Các câu trả lời đúc kết cho các câu hỏi nghiên cứu của đề bài

### 10.1 "Một AI agent nên duy trì tri thức chính xác về một hệ thống phần mềm hiện có như thế nào?"

**KHUYẾN NGHỊ.** Bằng cách lưu trữ rất ít, gắn nhãn cho mỗi thứ được lưu trữ bằng nguồn chân lý của nó, neo từng thứ được lưu trữ vào đoạn mã mà nó mô tả, và tái xác minh các neo một cách cơ học thay vì đọc lại các đoạn văn xuôi.

Cụ thể, câu trả lời gồm năm phần:

1. **Quy tắc kết nạp.** Chỉ lưu trữ một dữ kiện nếu một kỹ sư có năng lực không thể trích xuất lại nó từ code chuẩn mực (BMAD). Điều này loại bỏ hầu hết những gì mà các tài liệu kiến trúc do AI viết thường chứa đựng.
2. **Nhãn nguồn chân lý.** Mọi claim được lưu trữ đều khai báo artifact nào nắm giữ thẩm quyền đối với nó: `code`, `tests`, `config`, `spec`, `decision`, hoặc `derived`. Khi đó việc xử lý mâu thuẫn là một thao tác tra cứu, không phải một cuộc tranh luận.
3. **Các neo kèm xuất xứ.** Mọi claim đều liệt kê các neo `path#Symbol@sha` (Fiberplane). Lỗi thời = dấu vân tay AST đã chuẩn hóa của neo bị thay đổi kể từ `@sha`. Mang tính xác định, rẻ, không tốn lệnh gọi LLM.
4. **Bằng chứng được cơ giới hóa nơi có thể.** Quy tắc của claim được biên dịch thành một rule phụ thuộc, một bản diff hợp đồng, hoặc một bài test có tên bất cứ khi nào có thể (ArchUnit / dependency-cruiser / Tach / oasdiff / một test id). Các claim không thể cơ giới hóa được đánh dấu là `asserted` và được đếm số lượng.
5. **Phán quyết của con người khi có độ lệch.** Khi một neo bị lỗi thời, harness không bao giờ tự ý viết lại claim. Nó mở một mục drift với bốn phán quyết được phép (code sai / claim chưa từng đúng / thay đổi có chủ ý cần ADR / claim cần tinh chỉnh) và bắt buộc phải có một phán quyết được ghi nhận.

### 10.2 "Những gì thực sự nên lưu trữ so với những gì nên khám phá động?"

| Thông tin | Lưu trữ? | Nguồn chân lý | Tại sao |
|---|---|---|---|
| Cấu trúc thư mục, kiểm kê tệp | **Không** (phái sinh) | code | lệnh `ls`/glob trả lời được; lưu trữ nó đảm bảo chắc chắn sẽ bị lệch |
| Stack công nghệ + các phiên bản ghim | **Không** (phái sinh) | config | lockfile là chuẩn tắc; một bản lưu trữ copy chỉ là một sự dối trá chực chờ xảy ra |
| Bề mặt API được export | **Không** (phái sinh) | code | snapshot được sinh tự động, có thể diff |
| Đồ thị import/phụ thuộc | **Không** (phái sinh) | code | các công cụ của hệ sinh thái |
| Kiểm kê bài test, độ bao phủ | **Không** (phái sinh) | tests | test runner |
| Ranh giới component và *tên gọi* của chúng | **Có** | decision | code chỉ có thư mục; "ba thư mục này là một component với trách nhiệm này" là phán đoán của con người |
| Hướng phụ thuộc được cho phép | **Có**, dưới dạng tệp quy tắc | decision, thực thi bởi công cụ | không thể trích xuất lại từ đoạn code hiện đang tuân thủ |
| Các khái niệm và từ vựng domain | **Có** | decision | ý định đặt tên không nằm trong code |
| Các quy tắc domain / invariants | **Có**, kèm bài test giải tỏa | tests | code chỉ cho thấy *một* cách triển khai, không cho thấy đặc tính *bắt buộc* |
| Tại sao một thiết kế lại có hình thái như vậy | **Có** (ADR) | decision | hoàn toàn không có trong code, không bao giờ có |
| Các phương án thay thế bị từ chối | **Có** (ADR) | decision | vắng bóng trong code theo định nghĩa |
| Các ràng buộc từ bên ngoài repo (tuân thủ pháp lý, SLA, hợp đồng) | **Có** | decision | không nằm trong repo |
| Các cạm bẫy đã biết mà agent hay mắc phải | **Có** | bằng chứng quan sát được | tri thức xương máu; giá trị cao nhất trên mỗi dòng trong kho lưu trữ |
| Cấu trúc liên kết triển khai (Deployment topology) | **Có** nếu không có trong IaC, ngược lại thì phái sinh | config hoặc decision | nếu đã có Terraform, thì Terraform chính là sự thật |
| Chiến lược kiểm thử (những gì *bắt buộc* phải test thế nào) | **Có** | decision | bộ test suite hiện tại chỉ là bằng chứng của thực tiễn, không phải của chính sách |

**CÁCH DIỄN GIẢI.** Khuôn mẫu chung: **lưu trữ các phán đoán, phái sinh các dữ kiện.** Mọi dự án trong tài liệu tham chiếu đều lưu trữ dữ kiện tĩnh (`STACK.md`, `STRUCTURE.md` của GSD; `research.md` theo tính năng của Spec Kit) và đó chính là nơi tài liệu của họ mục rữa đầu tiên, bởi vì dữ kiện chính là thứ mà code có thể mâu thuẫn ở bất kỳ commit nào.

### 10.3 "Những kiểm tra nào có thể mang tính xác định và những kiểm tra nào đòi hỏi LLM?"

**Xác định (bắt buộc phải là script):** các artifact bắt buộc hiện diện đầy đủ theo track; thứ tự DAG được tôn trọng; quét các điểm đánh dấu chưa giải quyết (`[NEEDS CLARIFICATION]`, TBD/TODO/FIXME, `{template-token}`); cấu trúc tiêu đề requirement/scenario; mọi requirement có ≥1 scenario; tính duy nhất và đơn điệu của ID; mọi `REQ-###` được tham chiếu bởi ≥1 task; mọi task tham chiếu một `REQ-###` có thật; mọi `REQ-###` được giải tỏa bởi ≥1 test có tên tồn tại và đang pass; tính lỗi thời của neo dựa trên AST fingerprint; trường `truth-source` của claim là hợp lệ; mọi claim kiến trúc được đánh dấu `enforced` có một tệp quy tắc tồn tại và quy tắc đó pass; mức độ nghiêm trọng diff hợp đồng (oasdiff); thay đổi schema mà không có migration; hoàn thành các ô checkbox của task; sổ đăng ký khiếm khuyết trống hoặc đã được miễn trừ; mã thoát build / typecheck / lint / test; ngân sách token của tri thức nạp-liên-tục; dữ liệu xuất xứ git (`commits_behind`).

**Đòi hỏi LLM (mang tính tư vấn, không bao giờ là cổng duy nhất):** yêu cầu này có thực sự kiểm thử được không; hai yêu cầu này có mang cùng một ý nghĩa không; quy tắc này có thực thi được như văn bản đã viết không; bản thiết kế có thỏa mãn ý định của spec không; phương án tiếp cận được chọn có hợp lý không; phán quyết đúng cho mục drift này là gì (đề xuất, con người quyết định); review code về chất lượng; claim này có đáng để lưu trữ hay không.

**KHUYẾN NGHỊ.** Tỷ lệ này rất quan trọng: hãy hướng tới việc danh sách xác định đóng vai trò cổng kiểm soát và danh sách LLM đóng vai trò người đánh giá phản biện. Một harness mà các cổng kiểm soát chỉ là những prompt thực chất là một harness hoàn toàn không có cổng kiểm soát nào.

### 10.4 Đa-agent hay một agent với các skill?

**KHUYẾN NGHỊ. Một agent, nhiều skill, subagent chỉ được sử dụng thuần túy làm ranh giới ngữ cảnh.**

Bằng chứng: các nhân cách của BMAD thực chất chỉ là các skill trong một agent duy nhất; Superpowers đạt kết quả nhờ subagent-tươi-mới-cho-mỗi-task (cô lập ngữ cảnh), không phải từ nhân cách vai diễn; các mapper của GSD rẽ nhánh song song để cô lập và tránh chuyển giao ngữ cảnh; các tài liệu nghiên cứu về mục rữa ngữ cảnh giải thích tại sao sự cô lập lại có ích và hoàn toàn không nói gì về vai diễn. Hãy tạo một subagent khi: (a) công việc đòi hỏi một lượng lớn ngữ cảnh không được phép làm ô nhiễm phiên làm việc chính, (b) công việc độc lập và có thể chạy song song, hoặc (c) bạn cần một phán đoán *không bị thiên kiến ô nhiễm* (review lại công việc mà phiên chính đã làm). Tuyệt đối không bao giờ tạo subagent chỉ để đóng một vai nhân vật.

### 10.5 Tài liệu có phải là nguồn chân lý không?

**KHUYẾN NGHỊ. Không, và mã nguồn cũng không phải.** Mô hình chuẩn xác là *thẩm quyền theo từng dữ kiện (per-fact authority)*:

| Câu hỏi | Thẩm quyền |
|---|---|
| Hệ thống đang làm gì ngay lúc này? | code, cộng với các bài test đang pass |
| Hệ thống bắt buộc phải làm gì? | spec (các yêu cầu năng lực vĩnh viễn) |
| Đặc tính nào bắt buộc phải luôn luôn duy trì? | invariant claim, được giải tỏa bởi một bài test |
| Cấu trúc nào bắt buộc phải được tôn trọng? | architecture claim, được thực thi bởi một tệp quy tắc |
| Tại sao nó lại được thiết kế như thế này? | bản ADR |
| Hiện trạng hình thái của repo là gì? | các artifact phái sinh, được tạo lại |

Một "mâu thuẫn" chỉ có ý nghĩa giữa một claim và *thẩm quyền được khai báo của chính nó*. `architecture.md` nói PostgreSQL và code nói Redis không phải là mâu thuẫn giữa hai thực thể ngang hàng — nó hoặc là một claim lỗi thời có thẩm quyền (một quyết định, ghi trong ADR, thực thi bằng rule) bị code vi phạm, hoặc là một quyết định chưa được ghi thành tài liệu. Hai trường hợp đó có cách khắc phục hoàn toàn khác nhau, đó chính là lý do tại sao harness không được phép đoán mò.

---

## 11. Các hình thái thất bại cần thiết kế để phòng chống (đã quan sát được, không phải giả thuyết)

| # | Hình thái thất bại | Bằng chứng nó là có thật | Biện pháp đối phó của chúng ta |
|---|---|---|---|
| 1 | Các cổng chỉ dùng prompt bị lách luật bằng lý lẽ bao biện | Superpowers phải dùng `<EXTREMELY-IMPORTANT>` và bảng cờ đỏ để giữ kỷ luật | các cổng kiểm soát là các mã thoát lệnh |
| 2 | Tài liệu tự động đối soát theo code, quyết định bị mất | `drift_action: auto-remap` của GSD làm chính xác điều này | độ lệch đòi hỏi một phán quyết; chỉ pipeline thay đổi mới được sửa claim |
| 3 | LLM không nhìn thấy độ lệch khi chỉ có phần triển khai thay đổi | arXiv:2604.03447: sụt giảm từ −21 đến −43 điểm phần trăm | dùng các neo + các rule, không dùng phán đoán cảm tính |
| 4 | Các yêu cầu không bao giờ được giải tỏa bởi các bài test | Spec Kit: "Tests là OPTIONAL" | lệnh `verify` thất bại trên bất kỳ `REQ-###` nào không có test pass |
| 5 | Spec theo tính năng không bao giờ hội tụ thành tri thức hệ thống | Cấu trúc `specs/NNN-*/` của Spec Kit | gập lưu trữ kiểu OpenSpec |
| 6 | Lý do lập luận bị chôn vùi trong tài liệu lưu trữ | `changes/archive/*/design.md` của OpenSpec | ADR mang tính vĩnh viễn, là công dân hạng nhất, được tham chiếu bởi các claim |
| 7 | Nhiều kho tri thức cùng tồn tại, độ lỗi thời không nhất quán | GSD: 7 bản đồ + intel JSON + đồ thị + CONTEXT.md | chính xác một kho lưu trữ duy nhất, một quy tắc xuất xứ duy nhất |
| 8 | Chỉ dẫn bị phình to làm suy thoái năng lực agent | Nghiên cứu context rot của Chroma; quy tắc ngân sách của BMAD | ngân sách token cứng, không có lối thoát hiểm |
| 9 | Agent thích dọn dẹp xóa mất tri thức trụ cột | BMAD phải viết bốn căn cứ riêng biệt để ngăn chặn việc này | bốn căn cứ được thực thi tại thời điểm review |
| 10 | Tuyên bố thành công chỉ vì tests pass | GSD phải cần đến `broken-windows` để ngăn chặn | sổ đăng ký khiếm khuyết + miễn trừ tường minh chặn trạng thái `done` |
| 11 | Độ tươi mới dựa trên thời gian là hoàn toàn vô nghĩa | Ngưỡng 24h của `intel` trong GSD, sau đó bị thay thế bởi `graphify` dựa trên commit | chỉ dựa trên commit/fingerprint |
| 12 | Framework tăng trưởng nhanh hơn dự án nó phục vụ | GSD lên tới 44 capabilities / ~90 workflows; BMAD lên tới 2.4 MB | các ngân sách cố định trong `CONSTITUTION.md`, được review mỗi đợt release |
| 13 | Agent chạy lung tung mất kiểm soát trong nhiều giờ | mini-swe-agent thực thi các giới hạn bằng mã nguồn | ngân sách theo từng phase, quỹ đạo được lưu vết liên tục |
| 14 | Thay đổi schema/hợp đồng vượt qua xác minh một cách sai lệch | Cổng schema mang tính chặn của GSD sinh ra là vì điều này | các cổng chặn độ lệch quy trình (process drift) |

---

## 12. Những điều tôi chưa thể khẳng định chắc chắn

**CHƯA BIẾT.** Liệu bất kỳ framework nào trong số này có thực sự cải thiện kết quả một cách có thể đo lường được hay không. Không có dự án nào trong sáu dự án công bố một đánh giá thực nghiệm về chính phương pháp luận của họ. Superpowers kiểm tra xem *các agent có tuân thủ các skill của nó hay không*, đó là sự tuân thủ quy trình, không phải kết quả công việc. Những con số kết quả duy nhất trong tài liệu tham chiếu là các tuyên bố SWE-bench của mini-SWE-agent, vốn đo lường một vòng lặp trần trụi hoàn toàn không có phương pháp luận nào — và nó đạt điểm >74%. **Hoàn toàn không có bằng chứng nào trong tài liệu tham chiếu cho thấy một quy trình nặng nề giúp cải thiện chất lượng đầu ra của agent.** Hãy coi mọi tuyên bố về phương pháp luận ở đây, bao gồm cả của tôi, như một giả thuyết cần được kiểm chứng.

**CHƯA BIẾT.** Độ bền vững khi áp dụng trong thế giới thực. Tôi không tìm thấy bất kỳ báo cáo theo dõi dài hạn nào về một repository giữ được tầng tri thức hệ thống chính xác trong vòng một năm. Hạn chế của Fiberplane là rất đáng suy ngẫm: "Người dùng có thể liên kết lại mà không cập nhật văn xuôi." Mọi cơ chế neo đều có thể bị đánh bại bởi một con người chán nản hoặc một agent luôn tìm cách chiều lòng người dùng.

**CHƯA BIẾT.** Cơ chế neo bằng dấu vân tay AST đã chuẩn hóa hoạt động tốt đến mức nào trên một đợt tái cấu trúc thực tế (đổi tên một symbol, di chuyển một tệp). Thao tác đổi tên sẽ hiển thị dưới dạng lỗi thời trên mọi claim neo vào cái tên cũ. Các chiến lược giảm thiểu có tồn tại (phát hiện đổi tên của git, neo ở cấp symbol thay vì cấp đường dẫn) nhưng tôi chưa kiểm thử chúng trong thực tế. Đây là rủi ro triển khai lớn nhất trong đề xuất của tôi.

**CHƯA BIẾT.** Kích thước chuẩn xác của ngân sách tri thức nạp-liên-tục. Con số 400 dòng của tôi là một phép ngoại suy từ kỷ luật ngân sách được nêu của BMAD và các tài liệu nghiên cứu về context-rot, không phải là một số liệu đo lường thực nghiệm.

---

## 13. Nguồn tham khảo

Các repository (đọc trực tiếp từ mã nguồn tại các commit ở §0):
[obra/superpowers](https://github.com/obra/superpowers) ·
[github/spec-kit](https://github.com/github/spec-kit) ·
[Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec) ·
[bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) ·
[SWE-agent/SWE-agent](https://github.com/SWE-agent/SWE-agent) ·
[SWE-agent/mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) ·
[gsd-build/get-shit-done](https://github.com/gsd-build/get-shit-done) (archived) ·
[open-gsd/gsd-core](https://github.com/open-gsd/gsd-core)

Các bài báo khoa học:
[arXiv:2604.03447 — Measuring LLM Trust Allocation Across Conflicting Software Artifacts](https://arxiv.org/abs/2604.03447) ·
[arXiv:2609.00252 — Spec-Driven Development for Agentic Software Engineering](https://arxiv.org/html/2609.00252v1) ·
[arXiv:2606.04967 — From Prompt to Process](https://arxiv.org/pdf/2606.04967) ·
[arXiv:2309.12499 / doi:10.1145/3643757 — CodePlan](https://dl.acm.org/doi/10.1145/3643757) ·
[doi:10.1016/j.csi.2023.103774 — Architecture view-based drift analysis](https://dl.acm.org/doi/10.1016/j.csi.2023.103774)

Các công cụ và bài viết phân tích:
[Fiberplane drift linter](https://fiberplane.com/blog/drift-documentation-linter/) ·
[Aider repo map](https://aider.chat/2023/10/22/repomap.html) ·
[SCIP announcement](https://sourcegraph.com/blog/announcing-scip) ·
[ArchUnit](https://www.archunit.org/) ·
[dependency-cruiser](https://github.com/sverweij/dependency-cruiser) ·
[Tach](https://github.com/tach-org/tach) ·
[Deptrac](https://github.com/deptrac/deptrac) ·
[oasdiff](https://github.com/oasdiff/oasdiff) ·
[oasdiff breaking-change rules](https://www.oasdiff.com/docs/breaking-changes) ·
[Structurizr DSL](https://docs.structurizr.com/dsl) ·
[OpenHands AGENTS.md](https://github.com/OpenHands/OpenHands/blob/main/AGENTS.md) ·
[OpenHands skills](https://docs.openhands.dev/overview/skills) ·
[ADR tooling index](https://adr.github.io/adr-tooling/) ·
[log4brains](https://github.com/thomvaill/log4brains) ·
[Kiro (AWS)](https://aws.amazon.com/documentation-overview/kiro)
