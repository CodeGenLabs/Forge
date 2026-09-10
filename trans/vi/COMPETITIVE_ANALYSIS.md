# COMPETITIVE_ANALYSIS.md — Phân tích đối thủ cạnh tranh

Tài liệu đồng hành với [RESEARCH.md](RESEARCH.md). Tài liệu đó chứa đựng các bằng chứng thực nghiệm và các pinned commit; tài liệu này chứa đựng sự so sánh và các quyết định tiếp thu/chắt lọc. Các đánh giá xếp hạng thể hiện nhận định của tôi dựa trên mã nguồn đọc được vào ngày 2026-09-10, không phải dựa trên các tuyên bố quảng bá của nhà phát triển.

**Thang điểm đánh giá**

| Ký hiệu | Ý nghĩa |
|---|---|
| **A** | Mạnh mẽ, và được thực thi mang tính *cơ học* (bằng code, schema, mã thoát lệnh) |
| **B** | Hiện diện và được đặc tả tốt, nhưng chỉ được thực thi thông qua prompt |
| **C** | Hiện diện nhưng mỏng manh, chỉ một phần, hoặc mang tính tùy chọn |
| **–** | Hoàn toàn vắng bóng |

Sự phân biệt giữa **A** và **B** là mấu chốt của toàn bộ bảng này. Hầu hết các dự án này sẽ đạt điểm cao hơn nhiều trên một bảng đánh giá không hỏi câu hỏi: *thứ gì thực sự thực thi nó*.

---

## 1. Ma trận năng lực

| Năng lực | Superpowers | Spec Kit | BMAD | OpenSpec | SWE-agent (+mini) | GSD Core | Tốt nhất ngoài 6 dự án trên |
|---|---|---|---|---|---|---|---|
| Động não / khơi gợi ý định (Brainstorming / intent elicitation) | **B** router 3 nhánh, cổng phê duyệt cứng | **B** `/clarify`, `[NEEDS CLARIFICATION]` | **B** brainstorming + advanced-elicitation + party-mode | **B** `/opsx:explore` | – | **B** `discuss-phase` + các chế độ giả định | Kiro (đối thoại yêu cầu) |
| Điều tra mã nguồn hiện có (Investigation of existing code) | **C** tùy tiện (ad-hoc) trong skills | **C** `research.md` theo từng feature | **B** `deep-recon`, quét `project-context` | **C** `openspec list --specs` + đọc specs | **A** bản thân vòng lặp *chính là* điều tra (tái hiện trước) | **A** rẽ nhánh song song `map-codebase` | Aider repo map; SCIP/Glean |
| Đặc tả (Specification) | – (chỉ có tài liệu thiết kế) | **B** template phong phú, `FR-###`/`SC-###` | **B** SPEC kernel phái sinh từ memlog | **A** ngữ pháp requirement/scenario + `validate` | – | **B** `spec-phase`, `REQUIREMENTS.md` | – |
| Tri thức kiến trúc (Architecture knowledge) | – | – | **A** template spine + `lint_spine.py` | **C** chỉ có `design.md` theo từng thay đổi | – | **B** 7 bản đồ codebase + các vị từ trong `CONTEXT.md` | ArchUnit / dependency-cruiser / Tach / Deptrac; Structurizr DSL |
| Tri thức hệ thống (bền vững, toàn hệ thống) | – | – | **B** spine + khối quản lý trong AGENTS.md | **A** `openspec/specs/` (chỉ về hành vi) | – | **B** `.planning/codebase/` + `intel` + `graphs` | OpenHands `repo.md` + `memory/`; các tệp điều hướng Kiro |
| Quản lý thay đổi (Change management) | – (dùng git worktrees) | **C** `specs/NNN-*/`, không bao giờ hội tụ | **C** epics/stories | **A** change → delta → gập lưu trữ (archive fold) | – | **B** phases/milestones/waves | – |
| Lập kế hoạch tác vụ (Task planning) | **A** định dạng kế hoạch chặt chẽ, không có placeholder | **B** task nhóm theo story, đánh dấu `[P]` | **B** epics-và-stories | **B** các nhóm `## N.` + xác thực đánh số | – | **B** plan-phase + `gap-analysis` trên REQ ids | – |
| TDD | **A** RED-GREEN-REFACTOR là luật thép | **C** "Tests are OPTIONAL" | **B** trong build/review skills | **C** "nêu cách xác minh" theo từng task | **A** ngầm định (reproduce → fix → re-run) | **B** năng lực `tdd` với cổng RED/GREEN | – |
| Vòng lặp thực thi của agent (Agent execution loop) | **B** subagent cho mỗi task + review 2 giai đoạn | **B** `/implement` | **B** `bmad-build` / `build-auto` | **B** `/opsx:apply` với `tracks` | **A** bản triển khai tham chiếu chuẩn mực | **B** execute-phase theo các wave | – |
| Xác minh (Verification) | **B** bằng chứng trước khẳng định | **B** `/analyze` + `/checklist` (chỉ đọc) | **B** review skills + duyệt tiêu chí rubric | **B** verify-change (3 chiều, bằng prompt) | **A** tests là chân lý tối cao; sửa code có linter bảo vệ | **A** gate engine + `nyquist` + `broken-windows` | oasdiff / Schemathesis / Pact |
| Phát hiện độ lệch (Drift detection) | – | – | **C** dòng xuất xứ + `git log --diff-filter=DR` khi refresh | – | – | **A** các cổng structural + process + premise | **A** Fiberplane `drift` (neo AST-fingerprint) |
| Kỹ nghệ ngữ cảnh (Context engineering) | **A** cô lập subagent, ngữ cảnh tự dựng | **B** "tiết lộ lũy tiến" trong prompts | **B** persistent_facts, ngân sách kích thước, quy tắc truy xuất | **A** `instruction` theo artifact + `contextFiles` | **A** ngân sách bằng code, lưu vết trajectory liên tục | **A** cô lập phase, rẽ nhánh song song, ngữ cảnh tươi mới | Nghiên cứu mục rữa ngữ cảnh của Chroma |
| Khả năng truy vết (Traceability) | **C** plan trích dẫn đường dẫn spec | **B** kiểm kê ID dựng bằng suy luận LLM | **B** Bản đồ Capability → Architecture, `binds` | **B** đường dẫn capability là khóa kết nối | – | **B** `gap-analysis` đối chiếu chéo REQ-ID / D-ID | Thực hành truy vết yêu cầu (Requirements-traceability) |
| Cổng QA (QA gates) | **C** các trạm kiểm soát review | **C** thang đo mức độ, chỉ mang tính tư vấn | **C** cổng reviewer tiêu thụ JSON linter | **B** `validate` chặn bước archive | **A** giới hạn + revert khi lỗi linter | **A** các cổng khai báo với `blocking` | – |
| Khả năng thích ứng quy mô (Scale adaptation) | **A** spike/bounded/architectural + bánh cóc 1 chiều | **C** các preset (`lean`) | **B** `altitude`, "đúng kích cỡ" | **C** `skip_specs`, `design` tùy chọn | – | **B** `quick`/`fast`/`sketch`/`spike` so với phase đầy đủ | – |
| Tính xác định của công cụ nội bộ | **C** chỉ có hook + shell scripts | **C** chỉ có phân giải đường dẫn | **B** `lint_spine.py`, bộ phân giải config | **A** Zod schemas, parsers, validator, DAG, gập lưu trữ | **A** bản thân agent là code | **A** drift lib, gate engine, capability manifests | – |
| Chi phí áp dụng (càng thấp càng tốt) | **A** 14 skills, 3.4k dòng | **B** CLI + templates + `.specify/` | **–** 29 skills, 2.4 MB, các bộ phân giải Python | **B** Node CLI + cây thư mục `openspec/` | **A** không có (chúng ta chỉ tiếp thu ý tưởng) | **–** 44 capabilities, ~90 workflows | thay đổi |

### Ma trận này chỉ ra điều gì

1. **Không có dự án nào đạt điểm A ở cả hai mục "tri thức hệ thống" và "phát hiện độ lệch".** OpenSpec có tri thức hành vi bền vững nhưng không có câu chuyện phát hiện độ lệch; GSD có các cổng phát hiện độ lệch nhưng chạy trên tri thức là văn xuôi tự do; BMAD có *định dạng* tri thức tốt nhất nhưng không có cơ chế phát hiện độ lệch ngoài thao tác refresh thủ công. **Khoảng trống mà harness của chúng ta phải lấp đầy chính là giao điểm này.**
2. **Cơ chế phát hiện độ lệch đạt điểm A duy nhất tồn tại cho vấn đề này lại nằm ngoài 6 dự án** (neo AST-fingerprint của Fiberplane) và nó chỉ là một *bộ phát hiện (detector)*, không phải bộ giải quyết (resolver).
3. **Hai dự án thực thi mọi thứ bằng mã nguồn (OpenSpec, GSD) là những dự án đáng để sao chép về mặt cấu trúc.** Hai dự án thực thi bằng văn xuôi (Superpowers, Spec Kit) là những dự án đáng để sao chép về *từ vựng và tính kỷ luật*. BMAD đáng để sao chép *một template, một linter và một chính sách*. SWE-agent đáng để sao chép *ba cơ chế* và không có gì khác.
4. **Chi phí và năng lực tương quan nghịch theo hướng tiêu cực.** Hai dự án có năng lực cao nhất (BMAD, GSD) lại là hai dự án tốn kém nhất để sở hữu, chênh lệch cả một bậc độ lớn, và năng lực của chúng bị dàn trải qua hàng tá tính năng mà hầu hết các dự án sẽ không bao giờ chạm tới.

---

## 2. Đúc rút theo từng dự án

### 2.1 Superpowers — *Thư viện kỷ luật*

**Điểm mạnh.** Nhỏ gọn (3.377 dòng trên 14 skills). Mỗi skill là một artifact đã được kiểm thử với bộ test suite đỏ/xanh thực tế. Định dạng kế hoạch (plan format) là tốt nhất trong tài liệu tham chiếu: đường dẫn tệp chính xác, `Interfaces: Consumes/Produces` với chữ ký hàm thực tế, năm bước TDD với code nguyên văn, và điều cấm tường minh đối với các cụm từ placeholder chung chung. Bộ định tuyến 3 nhánh kèm bánh cóc một chiều (one-way ratchet) là câu trả lời mạch lạc nhất cho bài toán cân đối giữa quy trình và quy mô tác vụ.

**Điểm yếu.** Hoàn toàn không có mô hình hệ thống — không có kiến trúc, component, invariant, ADR hay mô hình dữ liệu, và không có gì bền vững sống sót sau một đợt thay đổi ngoài một tài liệu thiết kế có ghi ngày và một kế hoạch có ghi ngày. Việc thực thi hoàn toàn dựa trên cấp độ prompt, đó là lý do tại sao văn bản phải gào thét (`<EXTREMELY-IMPORTANT>`, "bạn không có sự lựa chọn"). `subagent-driven-development` cấm việc tạm dừng chờ con người ở giữa kế hoạch, điều này đúng cho thông lượng (throughput) nhưng lại sai đối với các cổng kiểm soát mà chúng ta thực sự cần. Quá trình bootstrap có thể bị mất sau khi ngữ cảnh bị nén (compaction) trên một số host.

**Tiếp thu.** Bộ định tuyến quy mô + bánh cóc 1 chiều · định dạng kế hoạch (files/interfaces/không-placeholder) · bằng-chứng-trước-khẳng-định · subagent tươi mới cho mỗi task · review 2 giai đoạn (tuân thủ spec ≠ chất lượng code) · TDD-cho-prompts với thư mục `tests/` · công bố tên skill khi chạy (announce-the-skill).

**Từ chối.** Sử dụng chữ in hoa cưỡng chế làm tầng thực thi · thực thi kế hoạch mà không có con người can thiệp (no-human-in-the-loop) · coi tài liệu thiết kế theo từng thay đổi là kho tri thức bền vững duy nhất.

**Chỉnh sửa.** `verification-before-completion` → `forge verify` tạo ra artifact bằng chứng có chữ ký. Checklist tự review của `writing-plans` → lệnh `forge check` mang tính xác định.

---

## 2.2 GitHub Spec Kit — *Hệ thống từ vựng*

**Điểm mạnh.** Từ vựng artifact tốt nhất: `FR-###`, `SC-###`, các user story được ưu tiên hóa và có thể kiểm thử độc lập kèm `Independent Test`, các tiêu chí thành công có thể đo lường và không phụ thuộc công nghệ, và `[NEEDS CLARIFICATION: …]` như một điểm đánh dấu sự mơ hồ có thể grep được trong nội dung. Một bản hiến chương có hiệu lực cao hơn spec, với các xung đột được tự động phân loại là CRITICAL. Lệnh `/analyze` là bản đặc tả bằng văn bản hoàn chỉnh nhất về một công cụ kiểm tra tính nhất quán mà tôi từng thấy. Khối ngăn xếp ghi đè template (template override stack) cho phép dự án tùy biến mà không cần fork. Khối `SYNC IMPACT REPORT` trong hiến chương của chính nó là một hạt giống ghi nhận tác động gọn gàng.

**Điểm yếu.** `specs/NNN-feature/` không bao giờ hội tụ thành tri thức hệ thống — sau N tính năng bạn có N ảnh chụp lịch sử nhưng không có mô tả nào về toàn thể hệ thống. Tests bị tuyên bố là TÙY CHỌN (OPTIONAL) trong template tác vụ trong khi template spec lại đòi hỏi các bài test độc lập, điều này làm đứt gãy chuỗi truy vết duy nhất có ý nghĩa. Lệnh `/analyze` yêu cầu LLM dựng danh mục ID bằng suy luận từ khóa rồi tính toán tỷ lệ phần trăm bao phủ "một cách xác định". Các hook được điều phối bằng cách yêu cầu mô hình đọc YAML rồi in ra dòng lệnh `EXECUTE_COMMAND:`. Bộ sáu tệp lập kế hoạch cho mỗi tính năng phần lớn là tiếng ồn hoặc tri thức hệ thống bị đặt sai chỗ.

**Tiếp thu.** Các ID yêu cầu/tiêu chí có nhãn rõ ràng · `[NEEDS CLARIFICATION]` như một điểm đánh dấu chặn có thể grep được · các user story được ưu tiên và kiểm thử độc lập · hiến chương cao hơn spec · ngăn xếp ghi đè template · phân tích mang tính chỉ-đọc · báo cáo tác động đồng bộ (sync-impact reporting).

**Từ chối.** Các thư mục tính năng được đánh số đóng vai trò là đơn vị tri thức bền vững · test tùy chọn · các hook được điều phối qua prompt · `/analyze` dưới dạng một prompt · bộ 6 tệp cồng kềnh cho mỗi tính năng.

**Chỉnh sửa.** Chia tách `/analyze`: `forge check` (xác định) + một đợt review ngữ nghĩa nhỏ. `research.md` / `data-model.md` / `contracts/` thôi không gắn theo từng tính năng nữa mà trở thành Tri thức Hệ thống hoặc các artifact phái sinh.

---

## 2.3 BMAD Method — *Định dạng tri thức*

**Điểm mạnh.** Ba thành phần thực sự xuất sắc:

1. `spine-template.md` — các khối `AD-n` với **Binds / Prevents / Rule**, ID ổn định không bao giờ bị đánh số lại, các bất biến kế thừa ở chế độ chỉ-đọc, chú thích nguồn chân lý tường minh (`Stack` chỉ là một *hạt giống - seed*, "mã nguồn nắm giữ chi tiết"), `Bản đồ Capability → Architecture`, mục `Deferred`, và trường `altitude`. Tiêu chí kết nạp của nó — *"những quyết định mà người xây dựng trong tương lai không thể đọc ra từ code chuẩn mực"* — là câu đơn xuất sắc nhất trong toàn bộ tài liệu tham chiếu.
2. `lint_spine.py` — một doc linter xác định mà docstring của nó nêu rõ sự phân chia công việc đúng đắn: "LLM đếm sai ID và bỏ sót các placeholder nguyên văn; grep thì không."
3. `bmad-project-context` — sổ cái (`retain | rewrite | relocate | automate | delete`), **bốn căn cứ để xóa bỏ**, dòng xuất xứ `Verified <date> against <sha>` cộng với việc tái xác minh `git log --diff-filter=DR`, "ưu tiên một kiểm tra tự động hơn một quy tắc văn xuôi", và một ngân sách kích thước không thể tự ý nâng lên.

Cộng thêm `.memlog.md` dạng append-only của `bmad-spec` với một tệp `SPEC.md` được phái sinh, giúp loại bỏ các xung đột chỉnh sửa tại chỗ và cung cấp khả năng truy xuất nguồn gốc miễn phí.

**Điểm yếu.** 29 skills, 2.4 MB, năm nhân cách agent, manifest TOML cho từng skill, hai bộ phân giải cấu hình bằng Python, và một builder để tiếp tục tạo thêm tất cả những thứ đó. Dùng con trỏ văn bản tự do `knowledge` làm cơ chế định tuyến. Không có gì kết nối các trường `Rule` có thể thực thi của spine với một công cụ thực thi thực tế, vì vậy spine có thể bị lệch trong âm thầm mặc dù nó là artifact sẵn sàng để kiểm tra nhất trong tài liệu tham chiếu. Không có vòng đời thay đổi nào giúp hội tụ tri thức.

**Tiếp thu.** Tiêu chí kết nạp · Cấu trúc Binds/Prevents/Rule với ID ổn định · Doc linter xác định và sự phân tách cơ học/ngữ nghĩa của nó · Các bất biến kế thừa chỉ-đọc · Chú thích nguồn chân lý tường minh · Dòng xuất xứ + tái xác minh các mục bị xóa kể từ SHA · Bốn căn cứ xóa bỏ · Sổ cái quản lý · Ưu tiên kiểm tra hơn quy tắc · Ngân sách kích thước không thể tự nâng · Log append-only với render phái sinh · Độ cao (altitude) · Bản đồ Capability → Architecture.

**Từ chối.** Các nhân cách (personas) · Bộ sinh skill (skill builder) · PRD/PRFAQ/brief/sprint/party-mode · Manifests TOML · Tầng phân giải cấu hình bằng Python · Bất kỳ thứ gì được đo bằng megabytes.

**Chỉnh sửa.** Chia tệp spine duy nhất thành các tệp theo chủ đề có kiểu định danh rõ ràng (các nguồn chân lý khác nhau, nhịp độ cập nhật khác nhau, để việc xác định lỗi thời theo từng tệp trở nên khả thi). Biên dịch `Rule` thành một tệp quy tắc phụ thuộc thực tế nếu hệ sinh thái hỗ trợ. Gộp linter vào kernel.

---

## 2.4 OpenSpec — *Khung xương cốt lõi*

**Điểm mạnh.** Mô hình lấy thay đổi làm trung tâm với ba tầng — vĩnh viễn `openspec/specs/`, đang thực hiện `openspec/changes/<name>/`, đã lưu trữ `changes/archive/YYYY-MM-DD-<name>/` — và cơ chế **gập lưu trữ mang tính xác định (deterministic archive fold)** các khối yêu cầu delta vào trong các spec vĩnh viễn. Đồ thị DAG artifact trong `schema.yaml` (`id`, `generates`, `template`, `instruction`, `requires`, cộng thêm `apply.requires`/`apply.tracks`) mang lại thứ tự thực hiện, trạng thái, câu lệnh gợi ý cho từng bước và định dạng đầu ra chỉ từ một tệp nhỏ gọn. Trạng thái được phái sinh từ hệ thống tệp, vì vậy không có gì bị mất đồng bộ. Việc xác thực là mã nguồn thực sự (Zod + các bộ parser viết tay + các issue ERROR/WARNING/INFO có kiểu rõ ràng + kiểm tra đánh số task và placeholder mục đích). Ngữ pháp delta là một tập hợp đóng với `MODIFIED` yêu cầu toàn bộ nội dung và `REMOVED` yêu cầu Lý do + Phương án chuyển dịch (Migration). Các thay đổi không có delta bị từ chối trừ khi `skip_specs: true` được ghi nhận trong repository. Mục `rules:` theo từng artifact trong `config.yaml` biến các ràng buộc của dự án thành hoạt động cụ thể mà không cần chạm vào bất kỳ skill nào. Mọi đường dẫn được sinh ra đều được kiểm tra tính bao hàm an toàn (containment check).

**Điểm yếu.** Tri thức vĩnh viễn của nó *chỉ* là các yêu cầu hành vi: không có component, ranh giới, hướng phụ thuộc, các invariant không quan sát được, mô hình dữ liệu, triển khai, hoặc lý do *tại sao*. Lý do lập luận nằm trong `design.md` theo từng thay đổi, vốn sẽ bị lưu trữ lại, vì vậy lý do một quyết định đang có hiệu lực tồn tại cuối cùng lại nằm trong `changes/archive/2026-01-06-.../design.md`. Lệnh `verify-change` chỉ là một prompt grep từ khóa. Initiatives / explorations / worksets / stores là sự phình to phạm vi đối với một lập trình viên cá nhân.

**Tiếp thu.** Mô hình thay đổi ba tầng · Lược đồ DAG artifact · Trạng thái phái sinh từ hệ thống tệp · Xác thực cấu trúc xác định với các issue có kiểu · Ngữ pháp delta đóng · Gập lưu trữ xác định đóng vai trò cơ chế đồng bộ tri thức · Từ chối zero-delta bằng một cơ chế bỏ qua *được nêu tên và ghi nhận* · Bơm quy tắc theo từng artifact · Lệnh `instructions --json` trả về chính xác các tệp mà một phase được phép đọc · Kiểm tra bao hàm đường dẫn trên mọi thao tác ghi.

**Từ chối.** Chỉ coi requirements là tri thức vĩnh viễn duy nhất · Đặt lý do lập luận trong các tài liệu thay đổi bị lưu trữ · `verify` dưới dạng một prompt · Các cấu trúc initiatives/explorations/worksets/stores.

**Chỉnh sửa.** Mở rộng tầng vĩnh viễn thành *capability specs + typed system-knowledge claims + ADRs*, và điều khiển thao tác gập từ một bản ghi tác động (impact record) tường minh theo từng thay đổi thay vì suy diễn tự động.

---

## 2.5 SWE-agent / mini-SWE-agent — *Vòng lặp bên trong (Inner loop)*

**Điểm mạnh.** mini là bằng chứng sống chứng minh rằng một vòng lặp ~200 dòng code chỉ dùng `bash` vẫn có tính cạnh tranh cao: ngân sách được thực thi bằng mã nguồn (`step_limit`, `cost_limit`, `wall_time_limit_seconds`, `max_consecutive_format_errors`), trajectory được lưu trong khối `finally` ở mỗi bước, một giao diện khiêm tốn nhưng trung thực, và một quy trình ưu tiên tái hiện lỗi trước. SWE-agent bổ sung thêm tri thức sâu sắc về ACI và một rào chắn kiểm soát mẫu mực: `windowed_edit_linting` so sánh diff của flake8 trước/sau khi sửa và **revert** nếu xuất hiện lỗi cú pháp mới, kèm theo thông điệp lỗi hướng dẫn cách thử lại.

**Điểm yếu.** Không có đặc tả, không có kiến trúc, không lưu trữ bền vững giữa các tác vụ, không có tri thức hệ thống — theo chủ ý thiết kế. Định hình theo benchmark: đưa issue vào, xuất bản vá ra. 15 gói công cụ của SWE-agent là một bề mặt quá lớn mà chúng ta sẽ phải bảo trì mà không thu lại lợi ích gì trên một host đã cung cấp sẵn các công cụ thao tác tệp và shell.

**Tiếp thu.** Ngân sách cứng bằng mã nguồn · Lưu vết trajectory ở mọi bước · Tái hiện trước khi sửa (reproduce-before-fix) · Quy trình một-hành-động-cho-mỗi-bước quan sát → hành động cho vòng lặp bên trong · Rào chắn trong công cụ kèm thông điệp hướng dẫn sửa lỗi · Cơ chế chọn phương án tốt nhất (best-of-n) với một reviewer tường minh chỉ dành cho các tác vụ quan trọng cao.

**Từ chối.** Xây dựng một engine thực thi, lớp trừu tượng môi trường hay client gọi mô hình riêng · Các gói công cụ tùy biến · Bộ khung phục vụ benchmark.

**Chỉnh sửa.** Vòng lặp bên trong vẫn thuộc về agent của host. Chúng tôi chỉ cung cấp *hợp đồng đầu vào* (task, phạm vi tệp được phép chạm, bài test bắt buộc phải chuyển từ đỏ sang xanh) và *hợp đồng đầu ra* (bằng chứng).

---

## 2.6 GSD Core — *Bộ máy thực thi (Enforcement engine)*

**Điểm mạnh.** Mô hình cổng khai báo: một điểm vòng đời có tên (`plan:pre`, `execute:wave:post`, `verify:post`, `ship:pre`, …), một kiểm tra được định danh bằng chuỗi truy vấn, `blocking: true|false`, một vị từ cấu hình `when`, và `onError: skip`. Ba cổng phát hiện độ lệch tạo thành một phân loại học thực thụ — **structural** (các thư mục/route/migration/barrel mới không có trong `STRUCTURE.md`, dựa trên ngưỡng, không chặn), **process** (các tệp schema thay đổi mà không có DB push → **chặn**), **premise** (một artifact phái sinh cũ hơn quyết định mới nhất trong `CONTEXT.md`). Dữ liệu xuất xứ trong frontmatter (`last_mapped_commit`, `built_at_commit`, `commits_behind`, `commit_stale`). Các vị từ một dòng có thể grep bằng máy trong `CONTEXT.md`, được trích dẫn theo ID và không bao giờ diễn giải lại. Cơ chế `broken-windows` đóng vai trò sổ đăng ký khiếm khuyết mang tính chặn kèm các miễn trừ được ghi nhận. Phân tích `gap-analysis` đối chiếu chéo REQ-ID với các kế hoạch. Các mapper song song tự ghi tệp của riêng chúng để không làm tràn ngữ cảnh của bộ điều phối. Kỷ luật bảo mật cẩn trọng (xác thực `built_at_commit` là mã hex trước khi truyền tới `git`).

**Điểm yếu.** 44 capabilities, ~90 tệp workflow, chỉ riêng tại `plan:pre` đã có 14 cổng kiểm soát, 4 cách biểu diễn cùng tồn tại cho cùng một hệ thống (bảy bản đồ markdown + `.planning/intel/*.json` + `.planning/graphs/` + các vị từ trong `CONTEXT.md`), mỗi thứ đều có câu chuyện lỗi thời riêng. Ngưỡng độ tươi mới 24 giờ của `intel` dựa trên thời gian và hoàn toàn vô nghĩa; việc sau này nó bị thay thế bởi tính lỗi thời theo commit trong `graphify` được xem như một sự thừa nhận nội bộ. Hành động `drift_action: auto-remap` âm thầm viết lại bản đồ cho khớp với code — chính xác là hành vi mà đề bài của chúng ta nghiêm cấm. Việc so khớp độ lệch cấu trúc chỉ là `structureMd.includes(prefix)` đối chiếu với văn xuôi tự do, do đó độ bao phủ thì cao nhưng độ chính xác lại rất thấp theo thiết kế.

**Tiếp thu.** Mô hình cổng khai báo · Phân loại độ lệch 3 hướng kèm chính sách chặn theo từng loại · Dữ liệu xuất xứ và tính lỗi thời dựa trên commit · Chỉ số `commits_behind` như một tín hiệu rõ ràng · Các vị từ một dòng được trích dẫn theo ID · Sổ đăng ký khiếm khuyết mang tính chặn kèm miễn trừ · Đối chiếu chéo độ bao phủ của requirement-ID · Các mapper rẽ nhánh tự ghi tệp riêng · Lập lại bản đồ gia tăng `--paths` với các đối số đã được xác thực · Tuyệt đối không để một giá trị lưu trữ truyền tới shell mà chưa qua kiểm định.

**Từ chối.** 44 capabilities · Đồ thị tri thức (knowledge graph) · Kho thông tin tình báo JSON song song · MCP memory · Độ tươi mới dựa trên thời gian thực · `auto-remap` làm mặc định · ~90 tệp workflow.

**Chỉnh sửa.** Một kho phái sinh duy nhất, một quy tắc xuất xứ duy nhất. `auto-remap` → `propose-remap`, tuyệt đối không bao giờ tự ý ghi đè lên một claim trụ cột nếu không có phán quyết được ghi nhận của con người.

---

## 3. Các dự án bổ sung đã làm thay đổi một quyết định

| Dự án / Nguồn | Đóng góp điều gì | Tiếp thu / Từ chối |
|---|---|---|
| [Fiberplane `drift`](https://fiberplane.com/blog/drift-documentation-linter/) | Các neo `path#Symbol@sha`; dấu vân tay AST tree-sitter đã chuẩn hóa; lỗi thời = fingerprint thay đổi kể từ baseline; định vị rõ ràng là "phát hiện, không phải review" | **Tiếp thu làm nguyên thủy phát hiện lỗi thời cốt lõi.** Hạn chế của nó ("người dùng có thể liên kết lại mà không cập nhật văn xuôi") cũng là hạn chế của chúng ta; giảm thiểu bằng cách yêu cầu một phán quyết, không phải một thao tác liên kết lại |
| [ArchUnit](https://www.archunit.org/) · [dependency-cruiser](https://github.com/sverweij/dependency-cruiser) · [Tach](https://github.com/tach-org/tach) · [Deptrac](https://github.com/deptrac/deptrac) | Hướng phụ thuộc, ranh giới tầng, cấm chu trình phụ thuộc, thực thi giao diện công khai — dưới dạng tests hoặc kiểm tra CI, tùy theo hệ sinh thái | **Tiếp thu làm mục tiêu thực thi cho các claim kiến trúc.** Không tự viết công cụ riêng; sinh/duy trì file cấu hình của chúng và lưu đường dẫn quy tắc làm bằng chứng (evidence) của claim |
| [oasdiff](https://github.com/oasdiff/oasdiff) (+ Pact, Schemathesis, Spectral) | Phân loại thay đổi phá vỡ tương thích (breaking-change) giữa hai tài liệu OpenAPI kèm cổng kiểm soát mức độ nghiêm trọng bằng exit-code | **Tiếp thu** cho việc phát hiện độ lệch giao diện khi dự án có hợp đồng giao diện được sinh tự động. **Từ chối** tự xây dựng giải pháp riêng ở đây |
| [Aider repo map](https://aider.chat/2023/10/22/repomap.html) | Trích xuất symbol bằng tree-sitter + thuật toán PageRank cá nhân hóa trên đồ thị tham chiếu, nằm trong ngân sách token | **Tiếp thu kết luận** (ngữ cảnh cấu trúc là rẻ và nên được khám phá thay vì lưu trữ cứng). **Từ chối tự xây dựng** — tính năng tìm kiếm của host agent cộng với grep là đủ dùng ở quy mô cá nhân |
| [SCIP](https://sourcegraph.com/blog/announcing-scip) / LSIF / Glean / Kythe | Năng lực hiểu code xuyên suốt các repository một cách chính xác ở quy mô lớn | **Từ chối đối với MVP** (chi phí bảo trì indexer). Chỉ xem xét lại nếu dự án phát triển vượt quá khả năng của grep |
| [Structurizr DSL](https://docs.structurizr.com/dsl) | Kiến trúc dưới dạng mã nguồn (Architecture-as-code) với một DSL có thể phân tích cú pháp; mô hình C4 | **Từ chối làm một dependency**, **tiếp thu ý tưởng** rằng mô hình component/ranh giới nên là dữ liệu có cấu trúc thay vì một sơ đồ vẽ trong văn xuôi |
| [OpenHands](https://github.com/OpenHands/OpenHands/blob/main/AGENTS.md) | `AGENTS.md` cho các quy ước nạp-liên-tục, `SKILL.md` cho tri thức được kích hoạt theo nhu cầu, phân tách `repo.md` + `memory/`; "liệt kê chính xác các mục bạn định lưu và chỉ lưu những gì người dùng phê duyệt" | **Tiếp thu sự phân tách hai tầng nạp-liên-tục/kích-hoạt và giao thức xác-nhận-trước-khi-lưu** |
| [Kiro (AWS)](https://aws.amazon.com/documentation-overview/kiro) | Bộ ba requirements/design/tasks + *các tệp điều hướng (steering files)* + *các hook khi save/create/commit* | **Tiếp thu như một sự xác nhận độc lập cho mô hình cổng kiểm soát.** Không nhập khẩu trực tiếp thứ gì |
| [Công cụ ADR](https://adr.github.io/adr-tooling/) · [log4brains](https://github.com/thomvaill/log4brains) · MADR | Thư mục ADR được đánh số, liên kết thay thế (supersession links), render trang tĩnh | **Tiếp thu định dạng** (`docs/system/decisions/ADR-NNNN-*.md` được đánh số, các phần chuẩn kiểu MADR, liên kết thay thế). **Từ chối các bộ công cụ đi kèm** — một thư mục và một quy ước đặt tên là đủ |
| [CodePlan](https://dl.acm.org/doi/10.1145/3643757) | Lan truyền thay đổi ở cấp độ repository kết hợp thần kinh-biểu tượng (neuro-symbolic): phân tích phụ thuộc gia tăng + phân tích phạm vi có thể ảnh hưởng + lập kế hoạch thích ứng | **Tiếp thu mô hình** cho phase impact (phân tích tĩnh đề xuất bán kính ảnh hưởng, mô hình chọn lọc). **Từ chối** tự triển khai phân tích phụ thuộc gia tăng |
| pytest-impact · OpenClover | Chọn lọc bài test dựa trên thay đổi từ git diff hoặc độ bao phủ theo từng bài test | **Tiếp thu nếu dự án đã có sẵn**; không bao giờ là điều kiện tiên quyết bắt buộc |
| Phát hiện mục rữa ngữ cảnh của Chroma | Chất lượng suy giảm theo độ dài đầu vào ở mỗi nấc tăng, từ rất lâu trước khi chạm giới hạn cửa sổ | **Tiếp thu làm căn cứ biện minh** cho ngân sách token nạp-liên-tục và sự cô lập phase |
| [arXiv:2604.03447](https://arxiv.org/abs/2604.03447) | LLM phát hiện lỗi tài liệu ở mức 67–94% nhưng giảm 21–43 điểm phần trăm khi chỉ có phần triển khai thay đổi; độ tự tin không mang lại thông tin | **Tiếp thu làm ràng buộc cứng**: LLM không được làm *bộ phát hiện* độ lệch, và độ tự tin của chúng không được làm yếu tố kích hoạt việc leo thang |
| [arXiv:2609.00252](https://arxiv.org/html/2609.00252v1) | Spec phải thực thi được / tường minh / có thể truy vết / giải tỏa được bằng bằng chứng; harness 8 cơ chế; tự chủ từng cấp độ | **Tiếp thu 4 đặc tính của spec làm tiêu chí chấp nhận** cho artifact spec của chúng ta, và tính tự chủ từng cấp độ làm mô hình cổng kiểm soát do con người duyệt |

---

## 4. Bảng tổng hợp đúc kết

Nguồn gốc của từng tầng trong harness của chúng ta, và những gì chúng ta bổ sung mà chưa ai có.

| Tầng | Nguồn chính | Nguồn phụ | Những gì chúng ta bổ sung |
|---|---|---|---|
| Cục bộ trong repository, ưu tiên tệp, coi git là database | OpenSpec | Superpowers | — |
| Vòng đời dưới dạng một artifact DAG được khai báo | `schema.yaml` của OpenSpec | — | Các biến thể DAG theo từng track được lựa chọn bởi bộ định tuyến quy mô |
| Thực thi vòng đời | Mô hình cổng của GSD | SWE-agent (rào chắn cấp công cụ) | Các cổng trở thành tầng thực thi *duy nhất*; prompts không bao giờ làm cổng |
| Thích ứng quy mô | Bộ định tuyến 3 nhánh của Superpowers | `altitude` của BMAD | Track lựa chọn các node DAG bắt buộc; bánh cóc một chiều và được ghi nhận |
| Định dạng spec | Ngữ pháp của OpenSpec | Từ vựng của Spec Kit | Mọi requirement phải nêu tên một test giải tỏa nó trước khi `verify` pass |
| Định dạng tri thức hệ thống | Spine của BMAD (`Binds`/`Prevents`/`Rule`, tiêu chí kết nạp) | Các vị từ trong `CONTEXT.md` của GSD | **Các claim có kiểu dữ liệu rõ ràng kèm các trường bắt buộc: `truth-source`, `anchors`, và `evidence`** |
| Phát hiện lỗi thời | Neo của Fiberplane | `commits_behind` của GSD | Neo được gắn theo từng claim, không phải theo từng tệp; `forge drift` mang tính xác định và chặn tiến trình khi cần phán quyết |
| Tuân thủ kiến trúc | ArchUnit / dep-cruiser / Tach / Deptrac | — | **Các claim được đánh dấu `enforced` phải nêu tên một tệp quy tắc tồn tại và pass; tỷ lệ `enforced`/`asserted` được báo cáo rõ ràng** |
| Đồng bộ tri thức | Gập lưu trữ của OpenSpec | `SYNC IMPACT REPORT` của Spec Kit | Việc gập được điều khiển bởi tệp `impact.md` được khai báo, và từ chối nếu có chỉnh sửa claim không được giải trình |
| Giải quyết độ lệch | — (chưa ai có) | Bốn căn cứ của BMAD | **Sổ cái độ lệch với 4 phán quyết; chỉ có pipeline thay đổi mới được sửa claim; nghiêm cấm việc tự động đối soát** |
| Khả năng truy vết | `gap-analysis` của GSD | Bản đồ Capability→Architecture của BMAD | Quy ước ID + grep + tệp `trace.json` *được sinh tự động*; không dùng database |
| Định dạng kế hoạch tác vụ | `writing-plans` của Superpowers | Đánh số `## N.` của OpenSpec | — |
| TDD | Superpowers | Năng lực `tdd` của GSD | Ràng buộc Requirement → test được kiểm tra một cách xác định |
| Vòng lặp thực thi bên trong | mini-SWE-agent | SWE-agent | Ủy quyền cho agent của host; chúng ta nắm giữ hợp đồng đầu vào/đầu ra và các ngân sách |
| Định nghĩa hoàn thành (Done) | `broken-windows` của GSD | Quy tắc bằng chứng của Superpowers | `verify` xuất ra báo cáo bằng chứng có chữ ký; các khiếm khuyết mở sẽ chặn `done` trừ khi được miễn trừ kèm lý do |
| Khởi tạo ban đầu (Bootstrap) | Rẽ nhánh `map-codebase` của GSD | Sổ cái tiếp nhận `project-context` của BMAD | Ba lượt duyệt: Kiểm kê xác định → Đề xuất ứng viên bằng LLM → **Phê chuẩn của con người kèm giới hạn số lượng claim** |
| Các cổng do con người duyệt | Cổng cứng của Superpowers | Quyền tự chủ từng cấp độ của arXiv:2609.00252 | Danh sách cố định, ngắn gọn, được liệt kê rõ ràng; mọi quyết định khác thuộc về agent |

**Điểm khác biệt cốt lõi trong một câu.** Mọi dự án trong tài liệu tham chiếu đều lưu trữ tri thức hệ thống dưới dạng văn xuôi tự do rồi cần một LLM để kiểm tra nó; chúng ta lưu trữ tri thức hệ thống dưới dạng một tập hợp nhỏ các claim được neo chặt, có gắn nhãn nguồn chân lý và kiểm tra chúng bằng git, tree-sitter, và các linter sẵn có của hệ sinh thái — chỉ dành LLM cho việc đề xuất các phán quyết mà con người sẽ xác nhận.
