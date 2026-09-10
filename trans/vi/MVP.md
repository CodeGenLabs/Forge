# MVP.md — Sản phẩm khả dụng tối thiểu

Thứ nhỏ nhất đáng để xây dựng. Được viết để một agent thứ hai hoặc một phiên làm việc khác có thể triển khai mà không cần phải đọc lại toàn bộ nghiên cứu: mọi thứ cần thiết đều nằm ở đây hoặc được trích dẫn chính xác.

**Mục tiêu:** một lập trình viên, ~2 tuần làm việc tập trung, ~2.000 dòng code Python cộng với 6 skill.

---

## 1. Luận điểm cốt lõi của MVP (The MVP thesis)

Xây dựng phần mà chưa ai từng xây dựng, và tiếp thu phần còn lại theo quy ước thay vì bằng mã nguồn.

Phần mà chưa ai xây dựng là: **các claim được neo, có gắn nhãn nguồn chân lý + phát hiện lỗi thời mang tính xác định + quy tắc chạm-claim giúp câu hỏi "tài liệu nào cần thay đổi?" có thể tính toán được.** Mọi thứ khác trong đề xuất này (DAG, gates, ngữ pháp delta, định dạng kế hoạch) đều đã tồn tại trong ít nhất một trong số 6 dự án và rất đáng để sao chép, nhưng sao chép nó trước tiên sẽ chỉ tạo ra thêm một framework vòng đời với tri thức bằng văn xuôi tự do.

Vì vậy, MVP được sắp xếp theo thứ tự nhằm chứng minh phần rủi ro từ sớm:

```
M0  khung sườn kernel + kho lưu claim + kiểm định           ← định dạng phải sống sót qua tiếp xúc thực tế
M1  các neo (anchors) + phát hiện độ lệch (drift)          ← RỦI RO LỚN NHẤT. Đo lường trước khi xây dựng thêm
M2  tầng phái sinh (derived tier) + chỉ mục truy vết (trace)
M3  DAG thay đổi + các cổng (gates) + một workflow (feature)
M4  sáu skill
M5  khởi tạo ban đầu (bootstrap)
```

**M1 có điều kiện dừng (stop condition).** Nếu tỷ lệ dương tính giả trên lịch sử commit phát lại tồi tệ đến mức sổ cái biến thành một mớ tiếng ồn (xem Q2 trong [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)), hãy dừng lại và thiết kế lại cơ chế neo trước khi viết tiếp M2–M5. Đó là lý do duy nhất khiến M1 đứng thứ hai thay vì đứng cuối cùng.

---

## 2. Các Milestone

### M0 — Khung sườn Kernel và kho lưu trữ claim (~2 ngày)

**Xây dựng.**

- Điểm nhập `forge`: điều phối lệnh con (subcommand), cờ `--json` trên mọi lệnh, mã thoát khác 0 khi thất bại, một định dạng issue duy nhất `{level, code, path, line, claim, message, fix}`.
- Trình phân tích claim: tiêu đề `### <ID> — <title>` theo sau bởi khối rào ```` ```claim ````, rồi đến văn xuôi. Phân tích khối rào dưới dạng YAML; không phân tích gì khác trong tài liệu. Các khối code fence được làm trắng trước khi quét regex để các ví dụ không bao giờ tạo dương tính giả, trong khi vẫn giữ nguyên số dòng (kỹ thuật từ `lint_spine.py` của BMAD).
- `forge check --scope store`: các kiểm tra S1–S11 và S16, S18 bên dưới.
- `forge claim new <kind>`, `forge claim show <ID>`.
- `forge init`: tạo khung cấu trúc `.forge/` và `docs/system/`.
- Template cho từng loại claim và cho các ADR.

**Các loại claim trong MVP: năm loại.** `architecture` (ARC), `component` (CMP), `concept` (CON), `invariant` (INV), `pitfall` (PIT). Hoãn lại: `interface` (API), `datum` (DAT), `workflow` (FLW), `constraint` (CST), `strategy` (STR) — chúng làm tăng bề mặt kiểm định mà không giúp kiểm chứng được ý tưởng cốt lõi.

**Tiêu chí nghiệm thu.** Một kho lưu trữ viết tay gồm 10 claim trải dài trên 5 loại vượt qua `forge check`, và mỗi kiểm tra từ S1–S11 đều có một fixture khiến nó thất bại với đúng mã lỗi và chuỗi `fix` hoạt động được.

---

### M1 — Các neo và độ lệch **(milestone rủi ro, ~3 ngày)**

> **Trạng thái: hoàn thành, 2026-09-10.** Kết quả và phán quyết nằm trong [docs/measurements/M1-anchor-stability.md](docs/measurements/M1-anchor-stability.md). Bốn điểm khác biệt so với kế hoạch ban đầu bên dưới, mỗi điểm đều có lý do:
>
> 1. **Được xây dựng trước M0**, theo chỉ đạo của người dùng, và đó là thứ tự tốt hơn: nếu phép đo thất bại, lược đồ claim ở M0 sẽ phải thay đổi. Đo lường trước khi chốt định dạng.
> 2. **Bổ sung `shifted` làm trạng thái thứ tư và hạ cấp `coarse` thành một cờ (flag).** Chỉnh sửa chỉ ở phần thân chiếm tới 79% các phán quyết không-tươi-mới; việc hiển thị chúng mặc định sẽ làm tăng gấp 4 lần kích thước sổ cái. Mục §5.1 của SYSTEM_KNOWLEDGE.md đã được cập nhật tương ứng kèm lý do.
> 3. **Chưa xây dựng `drift resolve`, `drift waive` và `reanchor`.** Cả ba đều ghi vào một tệp claim hoặc sổ cái, những thứ chưa tồn tại cho đến khi có M0. Thay vào đó, `forge drift` phân loại các neo được truyền trực tiếp qua dòng lệnh — đủ để kiểm tra milestone bằng tay và viết script tự động.
> 4. **Cần một bộ đo lường thứ hai.** Quá trình phát lại theo kế hoạch không thể đo được tỷ lệ dương tính giả, vì 600 commit lịch sử thực tế không chứa lần đổi tên thuần túy nào và không có commit nào chỉ sửa định dạng. Công cụ `tools/perturb_anchors.py` đã được tạo để tiêm các nhiễu có chân lý thực nghiệm đối chứng rõ ràng.

**Xây dựng.**

- Trình phân tích anchor: `path[#Symbol][@sha]`. Từ chối đường dẫn tuyệt đối, `..`, ký tự NUL, và bất kỳ SHA nào không phải là 4–40 ký tự hex **trước khi nó chạm tới `git`** (kỷ luật chống tiêm tùy chọn argv của GSD, áp dụng cho mọi anchor).
- Phân giải baseline: `@sha` của neo, nếu không có thì lấy commit cuối cùng chạm vào tệp claim. Sử dụng `git log --follow --find-renames` để tệp bị di chuyển vẫn phân giải được.
- Dấu vân tay (Fingerprint): phân tích bằng tree-sitter, băm chuỗi `(node_kind, token_text)`, loại bỏ khoảng trắng, comment và vị trí dòng. Nếu không có ngữ pháp → băm nội dung đã chuẩn hóa khoảng trắng, gắn cờ `coarse: true`.
- Thu hẹp symbol: định vị khai báo có tên trong cây cú pháp; một neo thư mục sẽ dùng git tree hash.
- Phân loại: `fresh` / `shifted` (phần thân thay đổi, signature giữ nguyên) / `stale` (signature thay đổi) / `missing` / `coarse`. Sự phân tách `shifted`/`stale` là khuyến nghị của Q2 và chi phí rất rẻ.
- `forge drift [--paths] [--changed] [--json]` → các phát hiện + `derived/drift.json`.
- `forge drift resolve <D> --verdict V1|V2|V3|V4 [--adr N] [--evidence T]` kèm bảng thực thi trong [SYSTEM_KNOWLEDGE.md](SYSTEM_KNOWLEDGE.md) §6.
- `forge drift waive <D> --reason --until`.
- `forge reanchor <ID>` — chỉ đóng dấu lại **khi và chỉ khi** fingerprint khớp theo ánh xạ đổi tên.
- Ghi thêm/đóng các mục trong `DRIFT.md`.

**Ngôn ngữ trong MVP: ba ngữ pháp.** TypeScript/TSX, Python, Go. Mọi thứ khác đi theo nhánh coarse. Ba ngôn ngữ là đủ để chứng minh cơ chế và bao phủ hầu hết các repo mà một lập trình viên cá nhân chạm tới.

**Cổng đo lường — bắt buộc thực hiện trước M2.** Chọn hai repo thực tế có lịch sử tái cấu trúc thực sự. Đặt 30 neo trên các symbol tiêu biểu. Phát lại 200 commit. Ghi nhận: số lượng `stale` giả trên mỗi commit, số lượng `missing` giả, và bao nhiêu trường hợp được giải quyết chỉ nhờ tính năng phát hiện đổi tên.

| Kết quả | Hành động |
|---|---|
| < 0.5 `stale` giả trên mỗi commit | tiếp tục như thiết kế |
| 0.5–2 | tiếp tục, nhưng mặc định sổ cái chỉ hiển thị `stale` (ẩn `shifted`), và xem xét lại độ chi tiết của neo |
| > 2 | **dừng lại.** Thiết kế lại theo Q2 — neo thô hơn, neo định vị theo nội dung, hoặc chỉ neo ở cấp component |

**Tiêu chí nghiệm thu.** Phép đo lường được chạy và ghi nhận trong repository này, kèm con số cụ thể và nhánh được chọn trong bảng.

---

### M2 — Tầng phái sinh và chỉ mục truy vết (~2 ngày)

> **Trạng thái: hoàn thành, 2026-09-10.** Đạt tiêu chí nghiệm thu: `forge trace INV-7` trả về các claim, test, change và tham chiếu ngược trên một kho fixture (`tests/test_trace.py::test_the_acceptance_case`), việc tái tạo là no-op (không thay đổi gì), và mọi artifact đều là văn bản LF đồng nhất từng byte với các khóa được sắp xếp. Món nợ M1 — định vị theo địa chỉ nội dung — đã được trả trước và đo lường lại: từ 0.61% → **0.00%** dương tính giả ([Báo cáo M1 §3.2](docs/measurements/M1-anchor-stability.md)).
>
> Năm điểm khác biệt, mỗi điểm đều có lý do:
>
> 1. **Không có trường `generated_at` trong phần bao bọc (envelope).** Dấu thời gian khiến mọi lần tạo lại đều khác nhau, do đó hai điều kiện "tái tạo là no-op" và "tệp phái sinh bị bẩn (dirty) là một lỗi" không thể cùng tồn tại. Commit ID mới là dữ liệu xuất xứ có ý nghĩa. Mục §2.3 của SYSTEM_KNOWLEDGE.md đã được đính chính.
> 2. **Ngữ pháp ID chấp nhận dạng slug, không chỉ là số.** Mục §7.1 từng ghi `PREFIX-\d+` trong khi mọi ví dụ trong cùng tài liệu đều dùng `CMP-payments`, `CON-capture`, `API-post-refunds`. Dạng slug thắng thế — `grep -r CMP-payments` tự thân nó đã rõ nghĩa. Thứ cần thực thi là tính ổn định, không phải tính chất chỉ gồm số.
> 3. **Chưa xây dựng `deps.json`.** MVP.md chỉ định "gọi công cụ phụ thuộc đã cấu hình của dự án", điều này thất bại trên bất kỳ repo nào không có sẵn công cụ đó; tự viết bộ phân giải import riêng sẽ tạo ra parser thứ hai và ngân sách kernel nên dành cho việc khác. Nó không nằm trong tiêu chí nghiệm thu và lệnh `forge impact` của M3 mới là thứ đầu tiên thực sự cần tới nó.
> 4. **Bổ sung `backrefs.json`.** Việc quét `forge:<ID>` cần một nơi để lưu trữ, và việc đưa nó vào index sẽ khiến index không thể tái tạo độc lập được.
> 5. **Một bộ phân tích claim tối giản (`store.py`) đã ra đời sớm.** Chỉ mục không thể tồn tại nếu không biết claim là gì. Nó chỉ phân tích cú pháp mà chưa kiểm định — M0 vẫn nắm giữ 18 kiểm tra của store.
>
> Hai vấn đề được phát hiện trong quá trình xây dựng, cả hai hiện đã được viết test:
>
> - **Các ví dụ trong tài liệu làm ô nhiễm chỉ mục.** `forge:ARC-3` bên trong một khối code minh họa, hay một lệnh nguyên văn `grep -r "forge:REQ-refunds-3"`, đã tạo ra các mục cho những claim chưa từng tồn tại. Văn xuôi hiện đã bị loại khỏi quá trình quét tham chiếu ngược: việc trích dẫn một ID là bình thường, chỉ code và các tệp quy tắc mới là nơi tuyên bố rằng chúng *thực thi (enforce)* claim đó.
> - **Tầng phái sinh tự biến nó thành vĩnh viễn lỗi thời.** Một tệp không thể mang ID của commit chứa chính nó, vì vậy việc commit một artifact vừa được phái sinh sẽ đóng dấu nó bằng commit cha của nó — và việc tạo lại để "sửa" điều đó lại tạo ra một commit khác tương tự. Trạng thái lỗi thời hiện bỏ qua các commit chỉ chạm vào tầng phái sinh, và tầng này tự loại trừ nó ra khỏi bản kiểm kê của chính nó.

**Xây dựng.**

- `forge sync derived [--paths]` tạo ra các tệp kèm frontmatter xuất xứ (`generated_from_commit`, `generator`, `tool`):
  - `inventory.json` — các tệp được theo dõi theo ngôn ngữ, số dòng code (LOC), điểm nhập (entry points), tệp test, stack + các phiên bản ghim từ lockfile;
  - `deps.json` — các cạnh module→module và chu trình phụ thuộc, bằng cách gọi công cụ phân tích phụ thuộc của dự án;
  - `tests.json` — tệp test → tên các test → các ID `@covers` mà mỗi test khai báo;
  - `trace.json` — chỉ mục truy vết.
- Tái tạo đồng nhất từng byte: chạy 2 lần tại cùng một commit phải tạo ra các tệp y hệt nhau. Lệnh `forge check` thất bại nếu tệp phái sinh bị bẩn (dirty).
- Trích xuất `@covers`: quét các tệp test tìm cú pháp `@covers <ID>[ <ID>…]` trong tên test hoặc comment liền kề.
- Trích xuất tham chiếu ngược `forge:<ID>` từ comment trong code và các tệp quy tắc.
- `forge trace <ID>` — truy vết hai chiều.
- `forge status` — xem trên một màn hình: track, phase, mục bị chặn, drift mở/miễn trừ, nợ kỹ thuật, ngân sách, tỷ lệ `enforced`/`asserted` theo loại, chỉ số `commits_behind`.

**Hoãn lại khỏi tầng phái sinh.** `api-surface.json` (cần khả năng phát hiện route theo từng framework mới thực sự hữu ích) và mọi bản đồ repo / PageRank (Q7 — là bước leo thang đầu tiên, không thuộc MVP).

**Tiêu chí nghiệm thu.** `forge trace INV-7` trả về các claim, test, change và tham chiếu ngược của nó trên một repo mẫu. Việc tạo lại là no-op. Thư mục `derived/` build được trên cả Windows và Linux với nội dung đồng nhất.

---

### M3 — DAG thay đổi, các cổng kiểm soát, một workflow (~3 ngày)

**Xây dựng.**

- Bộ nạp schema với các kiểm định kiểu OpenSpec: kiểm tra cấu trúc tương đương Zod, không trùng ID, các mục tiêu trong `requires` phải tồn tại, không có chu trình (thuật toán DFS báo cáo toàn bộ đường dẫn chu trình), mọi trường đường dẫn phải tương đối và an toàn về phạm vi bao hàm.
- Trạng thái phái sinh từ hệ thống tệp: một artifact hoàn thành khi và chỉ khi đường dẫn/glob trong `generates` tồn tại.
- Mô hình Track: trường `tracks` theo từng artifact, bao gồm cả điều kiện `B?`; việc nâng cấp một chiều được ghi nhận trong `changes/NNNN/.forge.yaml`.
- Hợp đồng ngữ cảnh `reads`; lệnh `forge instructions <artifact> --change N --json` giải quyết các tệp, các bộ chọn phái sinh và bộ chọn `claims:`.
- `forge gate <point>` với 12 cổng trong [ARCHITECTURE.md](ARCHITECTURE.md) §3.3.
- `forge impact --change N`: bán kính ảnh hưởng ứng viên (các tệp đã đổi/dự kiến đổi + phụ thuộc ngược từ `deps.json` + so khớp glob `CMP-`) và **tập hợp chạm-claim được tính toán**.
- Kiểm tra tính đầy đủ của việc giải trình chạm-claim (cơ chế thực thi cốt lõi, R5 bên dưới).
- Kiểm định ngữ pháp spec delta và gập lưu trữ mang tính xác định (ADDED / MODIFIED / REMOVED / RENAMED, kèm xác thực trước khi ghi của spec được dựng lại).
- `forge verify --change N` → `verification.json` kèm 8 điều kiện hoàn thành.
- `forge sync change N` — sáu thao tác tuần tự, từ chối ngay ở thất bại đầu tiên.
- `forge change new|track`, `forge archive`.
- **Một lược đồ workflow: `feature.yaml`**, phục vụ các track A/B/C.

**Tiêu chí nghiệm thu.** Một lần chạy end-to-end có viết script trên một repo mẫu: tạo một change, viết artifact bằng tay, quan sát từng cổng bị fail vì đúng lý do khi artifact có lỗi, sau đó pass; xác minh; đồng bộ; `@sha` của claim tịnh tiến; spec delta được gập lại; `forge status` sạch sẽ.

---

### M4 — Các Skill (~2 ngày)

**Sáu skill cho MVP** (ba trong số chín skill được hoãn lại):

| Skill | Ghi chú |
|---|---|
| `forge` (router) | Phân loại track, phát biểu lại ý định, cổng G1. Bao gồm bánh cóc một chiều và rào chắn "quá đơn giản không cần spec" |
| `investigate` | Subagent tươi mới; tự ghi tệp riêng; đưa ra các ứng viên kèm độ tin cậy |
| `specify` | Các yêu cầu delta + kịch bản; bơm các quy tắc `rules.spec` |
| `plan-tasks` | Định dạng kế hoạch của Superpowers với các thẻ `[REQ-*]` và không có placeholder |
| `implement` | Thực thi một task, theo TDD, phạm vi tệp, ngân sách |
| `curate-knowledge` | Chỉnh sửa claim, ghi sổ cái, đề xuất phán quyết độ lệch (chỉ dạng thu hẹp của Q8) |

Hoãn lại: `assess-impact` (kernel tự tính toán tập hợp; agent chọn lọc nội dòng trong phase `impact` mà không cần skill riêng cho đến khi hình thái rõ ràng), `design` (skill `specify` tạm thời bao phủ phần thiết kế của track C), `review` (sử dụng skill code-review có sẵn của host cho MVP).

Mọi skill: ≤250 dòng, markdown thuần không có cú pháp riêng của host, công bố khi bắt đầu, ưu tiên kernel trước, không dùng ngôn ngữ cưỡng chế, và có một bài kiểm thử áp lực trong `tests/skills/<name>/` vốn sẽ thất bại nếu thiếu skill.

**Tiêu chí nghiệm thu.** Bài kiểm thử áp lực của mỗi skill cho thấy một lần chạy baseline thất bại và một lần chạy thành công. Một thay đổi thuộc track-B chạy end-to-end thông qua các skill trên một repo mẫu.

---

### M5 — Khởi tạo ban đầu (Bootstrap) (~2 ngày)

**Xây dựng.**

- `forge bootstrap derive` — lượt 1, phái sinh thuần túy, chưa có claim nào. Đây là phần lớn phác thảo bootstrap của đề bài và nó hoàn toàn mang tính xác định.
- `forge bootstrap review` — lượt 3: duyệt các ứng viên theo thứ tự loại có giá trị cao nhất trước, từng nhóm ≤8 mục, mặc định từ chối, lồng ghép các câu hỏi `Uncertain`, không bao giờ hỏi những gì một lệnh quét có thể trả lời.
- `forge bootstrap seal` — ghi các claim đã được phê chuẩn với các neo được đóng dấu tại HEAD, `OVERVIEW.md`, `ADR-0001-adopt-forge.md` ghi nhận những gì *chưa* được phê chuẩn và mức trần đang áp dụng, cùng `.forge/config.yaml` với các lệnh đã được phát hiện.
- Kiểm định ứng viên: bắt buộc có neo, linter tiêu chí kết nạp, không tự bịa lý do lập luận, các invariant phải nêu tên code thực thi hoặc bài test chứng minh.

Lượt 2 (sinh ứng viên) là một **skill**, không phải mã nguồn kernel: các subagent song song theo từng chủ đề tự ghi trực tiếp vào `candidates/<topic>.md`. Theo Q14, MVP sẽ ưu tiên nạp trước `CON-` và `PIT-` — từ vựng và các cạm bẫy đã biết — thay vì quét tìm component và kiến trúc.

**Tiêu chí nghiệm thu.** Chạy bootstrap trên chính repository này và trên một repo bên ngoài thực tế. Ghi nhận kết quả: bao nhiêu ứng viên, bao nhiêu mục được phê chuẩn, cuộc review kéo dài bao lâu, và những loại nào thực sự hữu ích trong phase `investigate` đầu tiên diễn ra sau đó.

---

## 3. Các kiểm tra xác định trong MVP

Mỗi kiểm tra đều là một script. Mã lỗi là ổn định; mỗi lỗi đều mang theo một gợi ý `fix`.

### Cấu trúc (Store)

| # | Mã lỗi | Phép kiểm tra | Mức độ |
|---|---|---|---|
| S1 | `store.id_format` | ID khớp với `^(ARC\|CMP\|CON\|INV\|PIT)-(\d+\|[a-z0-9][a-z0-9-]*)$` — số hoặc slug kebab | ERROR |
| S2 | `store.id_unique` | ID là duy nhất trên toàn bộ kho; tăng dần trong một tệp; không bao giờ tái sử dụng | ERROR |
| S3 | `store.claim_fence` | Khối rào `claim` đúng định dạng; phân tích cú pháp được dưới dạng YAML | ERROR |
| S4 | `store.required_fields` | `kind`, `status`, `truth-source`, `anchors`, `reviewed` hiện diện và nằm trong phạm vi cho phép | ERROR |
| S5 | `store.anchor_required` | `anchors` không được rỗng trừ khi loại ∈ {concept} (MVP: tạm thời chưa có `constraint`) | ERROR |
| S6 | `store.evidence_required` | `status: enforced` ⇒ `evidence` không được rỗng và mọi mục đều phân giải được | ERROR |
| S7 | `store.adr_required` | `kind: architecture` ⇒ `since` hiện diện và tệp ADR tương ứng phải tồn tại | ERROR |
| S8 | `store.governs_dag` | Các mục tiêu trong `governs` phải tồn tại, không tự tham chiếu, không có chu trình | ERROR |
| S9 | `store.placeholder` | Không chứa TBD/TODO/FIXME/XXX/`{token}`/`[NEEDS CLARIFICATION`/`similar to <ID>` (các khối code fence được làm trắng) | ERROR |
| S10 | `store.candidate_isolation` | Không có trường `confidence` bên ngoài thư mục `candidates/`; mọi ứng viên đều có `status: proposed` | ERROR |
| S11 | `store.prose_present` | Phần thân văn xuôi phải có ≥2 dòng không trống | ERROR |
| S12 | `store.anchor_missing` | Mọi đường dẫn/symbol của neo đều phải tồn tại tại HEAD | ERROR |
| S13 | `store.derivable_smell` | >60% định danh trong văn xuôi xuất hiện trong các neo của nó **và** không có động từ khuyết thiếu (modal verb) | WARNING |
| S14 | `store.listing_smell` | Claim `CMP-` có đường dẫn glob nhưng có dưới 15 từ giải thích | WARNING |
| S15 | `store.stack_fact_smell` | Văn xuôi chứa mẫu phiên bản đứng cạnh tên một package | WARNING |
| S16 | `store.budget` | Tập hợp nạp-liên-tục nằm trong giới hạn `budgets.always_loaded_lines` | ERROR |
| S17 | `store.orphan` | Không có `governs` trỏ tới, không có tham chiếu ngược `forge:<ID>`, không được trích dẫn bởi N thay đổi gần nhất | WARNING |
| S18 | `store.retire_ground` | `status: retired` ⇒ phải có căn cứ được ghi nhận từ 1–4 kèm bằng chứng | ERROR |

### Quan hệ (Xuyên suốt các artifact)

| # | Mã lỗi | Phép kiểm tra | Mức độ |
|---|---|---|---|
| R1 | `trace.backref_valid` | Mọi `forge:<ID>` đều phải nêu tên một claim đang tồn tại và chưa bị retire | ERROR |
| R2 | `trace.evidence_test_exists` | Mọi `evidence: test:` đều phải xuất hiện trong `tests.json` | ERROR |
| R3 | `trace.evidence_rule_exists` | Mọi id `evidence: rule:` đều phải tồn tại trong tệp quy tắc được nêu tên | ERROR |
| R4 | `trace.requirement_task_coverage` | Mọi `REQ-*` được tham chiếu bởi ≥1 task; mọi task tham chiếu ≥1 `REQ-*` hoặc là task `chore` | ERROR |
| R5 | `trace.claim_touch_complete` | **Mọi claim trong tập hợp chạm-claim được tính toán đều phải được giải trình trong `impact.md`** | ERROR |
| R6 | `trace.superseded_has_adr` | Mọi mục `Superseded` đều phải nêu tên một ADR hiện có với trường `supersedes` tương ứng | ERROR |
| R7 | `trace.requirement_discharged` | Mọi `REQ-*` phải có ≥1 test pass mang thẻ `@covers` của nó | ERROR |
| R8 | `graph.requires_satisfied` | `requires` của DAG được thỏa mãn cho mọi artifact đang hiện diện | ERROR |
| R9 | `graph.track_artifacts` | Các artifact bắt buộc phải hiện diện đầy đủ theo track đã khai báo | ERROR |
| R10 | `derived.clean` | Việc tái tạo là no-op; `generated_from_commit == HEAD` tại thời điểm verify | ERROR |
| R11 | `derived.freshness` | `commits_behind ≤ thresholds.derived_stale_commits` | WARNING (chuyển thành ERROR tại `implement:pre`) |
| R12 | `spec.grammar` | Tiêu đề Requirement/scenario; ≥1 scenario cho mỗi requirement; dùng SHALL/MUST; MODIFIED có nội dung đầy đủ; REMOVED có Lý do+Chuyển đổi | ERROR |
| R13 | `spec.nonempty_or_skip` | Thay đổi zero-delta bị từ chối trừ khi có `skip_spec: true` kèm lý do | ERROR |
| R14 | `task.format` | Đường dẫn tệp chính xác, thẻ `[REQ-*]`, lệnh verify, chữ ký `Consumes`/`Produces`, không có placeholder | ERROR |
| R15 | `task.interface_consistency` | `Produces` trong task N khớp với `Consumes` trong task M theo tên và kiểu dữ liệu | ERROR |
| R16 | `task.scope` | Git diff của một task chỉ được phép chạm vào các tệp mà nó khai báo | ERROR |
| R17 | `drift.open_blocking` | Không có mục `DRIFT.md` nào đang mở mà chưa được miễn trừ trên một claim thuộc tập chạm của change này | ERROR |
| R18 | `debt.open_blocking` | Không có mục `DEBT.md` nào đang mở mà chưa được miễn trừ do chính change này tạo ra | ERROR |
| R19 | `verify.definition_of_done` | Đạt đủ tám điều kiện hoàn thành | ERROR |
| R20 | `repo.clean` | Tại `converge`: các task đã được tích chọn, archive hoàn tất, `forge check` toàn repo đều pass | ERROR |

**39 kiểm tra xác định.** Để so sánh, toàn bộ bề mặt kiểm tra xác định của Spec Kit chỉ là "tệp này có tồn tại hay không".

### Các kiểm tra bằng LLM trong MVP — năm kiểm tra, tất cả đều mang tính tư vấn

1. Mỗi yêu cầu có thể kiểm thử được như văn bản đã viết không? Có hai yêu cầu nào mang cùng một ý nghĩa không? (phase `spec`)
2. Có lý do `Unaffected` nào bị sai không; có consumer nào mà phân tích tĩnh không nhìn thấy không (hàng đợi queue, cron, client SDK, câu truy vấn dashboard)? (phase `impact`)
3. Một kỹ sư mới toanh có thể thực thi task này chỉ từ văn bản của nó không; có task nào đang làm hai việc cùng lúc không? (phase `tasks`)
4. Git diff này có thỏa mãn task của nó và chỉ task của nó không; chất lượng code có chấp nhận được không? (review theo từng task, hai giai đoạn)
5. Claim được đề xuất này có thỏa mãn tiêu chí kết nạp không — một kỹ sư có năng lực có thể đọc ra nó từ code chuẩn mực không? (`sync`, tại cổng G5)

Mọi thứ khác mà tài liệu tham chiếu thực hiện bằng prompt, MVP thực hiện bằng một script hoặc không làm.

---

## 4. Những gì MVP KHÔNG xây dựng

| Không xây dựng | Lý do | Khi nào xem xét lại |
|---|---|---|
| Đa nhân cách agent | Chỉ là trang phục hóa trang, không tăng năng lực (RESEARCH.md §5.2) | Không bao giờ |
| Đồ thị tri thức / Graph DB | Của GSD đã trở thành cách biểu diễn thứ tư mang theo sự mục rữa riêng | Chỉ khi bộ đôi `governs` + `trace.json` chứng minh là thất bại rõ rệt |
| Embeddings / RAG trên kho tri thức | 40 claim hoàn toàn nằm gọn trong một lệnh grep; điểm nghẽn là niềm tin, không phải việc truy xuất | Không bao giờ ở quy mô này |
| Chỉ mục code (SCIP / LSIF) | Tìm kiếm của host + tree-sitter + công cụ phụ thuộc là đủ | Khi `investigate` liên tục làm nổ ngân sách số bước (Q7); và khi đó sẽ làm dưới dạng repo-map phái sinh, không làm server chỉ mục |
| Execution engine / client gọi mô hình | Host đã có sẵn; mini-SWE-agent chứng minh ~200 dòng là đủ cạnh tranh | Không bao giờ |
| MCP server | Kernel là một CLI; một CLI có thể kết hợp với mọi host | Nếu một host không thể gọi shell ra ngoài |
| `api-surface.json` và các loại claim API/DAT | Cần phát hiện route và schema theo từng framework mới hữu ích | M6, cho một dự án có public HTTP API |
| Cổng hợp đồng `oasdiff` | Phụ thuộc vào điều trên | Đi cùng với các claim API |
| Bộ sinh quy tắc kiến trúc | Tự bảo trì file cấu hình của công cụ hệ sinh thái bằng tay và liên kết nó qua `evidence: rule:` — việc sinh tự động cấu hình thực chất là viết một trình biên dịch | Sau khi cơ chế liên kết chứng minh hữu ích trên 5+ claim |
| Nhiều lược đồ workflow | `feature.yaml` với ba track đã bao phủ tính năng mới, sửa bug (dưới dạng track B) và tái cấu trúc (`skip_spec`) | M6: `bugfix.yaml` cho artifact bắt buộc `reproduce` |
| `analyze` dưới dạng một phase | Nó chỉ là một cổng kiểm soát (Q9) | Nếu các kiểm tra ngữ nghĩa của LLM chứng minh xứng đáng với lượng token bỏ ra |
| Log quyết định append-only | Giải quyết bài toán nhiều người cùng ghi mà chúng ta không gặp phải (Q6) | Nếu việc ghi tri thức đồng thời trở thành hiện thực |
| Kho tri thức xuyên suốt các dự án | Là sở thích cá nhân, không phải tri thức hệ thống (Q11) | Không bao giờ đưa vào harness |
| Manifest plugin đa host | Superpowers phải trả giá ~15KB script đồng bộ cho việc này (Q12) | Khi hỗ trợ host thứ hai, và khi đó chỉ làm dưới dạng một manifest |
| Thư mục `rules/` văn xuôi, `workflows/`, `state/` | Lần lượt là sự phân kỳ, xây dựng thừa thãi, và sự giả tạo (ARCHITECTURE.md §3.1) | Không bao giờ |
| `forge stats` | Cần dữ liệu từ quá trình sử dụng thực tế trước | Sau khoảng ~10 thay đổi (Q1) |

---

## 5. Định nghĩa hoàn thành (Definition of Done) cho MVP

1. `forge check` vượt qua trên chính kho lưu trữ `docs/system/` của repository này.
2. Phép đo lường neo M1 được chạy và con số của nó được ghi nhận tại đây.
3. Một thay đổi thực tế được đưa đi end-to-end qua track C trên một repository thực tế, và kho lưu trữ claim thu được là thứ mà một con người muốn giữ lại.
4. Một độ lệch được chủ ý tạo ra (thay đổi một symbol mà một invariant đang neo vào), lệnh `forge drift` phát hiện ra nó, sổ cái đề xuất một phán quyết, và một phán quyết V3 được ghi nhận kèm một ADR khép lại vấn đề — **mà claim tuyệt đối không bao giờ bị tự động viết lại**.
5. Thử thực hiện một thay đổi trong đó một claim bị chỉnh sửa mà không được giải trình, và lệnh `forge sync` từ chối thực hiện.
6. `forge status` hiển thị vừa vặn trên một màn hình.
7. Số dòng code (LOC) của kernel dưới 2.500; 6 skill, mỗi skill ≤250 dòng; 12 cổng kiểm soát.
8. Mọi nguyên tắc trong [CONSTITUTION.md](CONSTITUTION.md) đều có trường `Cơ chế` được kiểm chứng đối chiếu với mã nguồn triển khai, và các nguyên tắc định hướng được dán nhãn lại một cách trung thực.

Tiêu chí 4 và 5 là những tiêu chí thực chất. Đó là hai hành vi mà không có công cụ hiện hữu nào có được, và nếu chúng hoạt động thì thiết kế được xác thực; nếu chúng gây phiền toái trong thực tế, thiết kế đã sai lầm theo cách mà việc đọc thêm tài liệu sẽ không bao giờ phát hiện ra được.

---

## 6. Nếu tôi phải xây dựng thứ này từ con số 0 hôm nay

*(Câu hỏi cuối cùng của bản tóm lược nhiệm vụ, được trả lời trực tiếp.)*

### Những gì tôi sẽ xây dựng

**Một kernel CLI mang tính xác định khoảng ~2.000 dòng code cộng với sáu skill markdown, mà đóng góp mới mẻ duy nhất là anchored claim (khẳng định có neo).**

Cụ thể, theo thứ tự ưu tiên:

1. **Claim** — một ID ổn định, một `truth-source`, các `anchors` trỏ vào code, `evidence` khi có thể thực thi tự động, và văn xuôi nói lên điều mà mã nguồn không thể tự nói. Đây là toàn bộ ý tưởng. Mọi thứ khác chỉ là hệ thống đường ống xung quanh nó.
2. **Phát hiện lỗi thời mang tính xác định** — dấu vân tay AST của tree-sitter so sánh với SHA được ghi nhận của neo. Không phải là "tài liệu này có đúng không" (câu hỏi không thể trả lời) mà là "đoạn code mà claim này mô tả có bị thay đổi kể từ lần cuối cùng con người xác nhận hay không" (trả lời được trong vài mili-giây, và là chính xác tập hợp mà một reviewer cần).
3. **Quy tắc chạm-claim (The claim-touch rule)** — đối với mỗi thay đổi, tính toán các claim có neo hoặc glob giao cắt với git diff, và từ chối đi tiếp cho đến khi mỗi claim được giải trình rõ ràng là không bị ảnh hưởng (unaffected), được cập nhật (updated) hoặc bị thay thế (superseded). Điều này biến câu hỏi "tài liệu nào bắt buộc phải thay đổi vì đợt triển khai code này?" từ một phán đoán cảm tính thành một phép toán tập hợp. Đó là cơ chế mà tôi không thể tìm thấy ở bất kỳ đâu trong tài liệu tham chiếu và là thứ tôi sẽ xây dựng đầu tiên nếu tôi chỉ được phép xây dựng một thứ duy nhất.
4. **Sổ cái độ lệch với 4 phán quyết, không có con đường tự động đối soát.** Kernel không có lệnh nào tự động viết lại một claim từ code. Sự vắng mặt đó là một tính năng, và nó được biện minh trực tiếp bởi các phép đo lường: LLM mất từ 21–43 điểm phần trăm độ chính xác phát hiện trong chính trường hợp code-thay-đổi-nhưng-tài-liệu-không-đổi, và độ tự tin của chúng không phân biệt được câu trả lời đúng hay sai.
5. **Ràng buộc các claim kiến trúc vào chính công cụ tuân thủ sẵn có của hệ sinh thái.** Đối với tập hợp con các claim kiến trúc có thể viết thành một quy tắc phụ thuộc (dependency rule) — vốn là hầu hết những claim thực sự quan trọng — việc "phát hiện độ lệch kiến trúc" thực chất là một bài toán linting đã có lời giải mà chưa ai trong tài liệu tham chiếu kết nối lại. Một claim được đánh dấu `enforced` sẽ nêu tên một quy tắc; quy tắc đó nêu tên claim; cả hai đều được kiểm tra tự động.
6. **Vòng đời, được tiếp thu toàn bộ**: artifact DAG và gập lưu trữ của OpenSpec, các cổng khai báo của GSD, bộ định tuyến quy mô và định dạng kế hoạch của Superpowers, từ vựng yêu cầu của Spec Kit, các ngân sách của mini-SWE-agent. Không có điều nào trong số này là mới mẻ và tất cả chúng đều hoạt động hiệu quả. Tôi sẽ không lãng phí dù chỉ một ngày để sáng tạo lại những phần này.

### Những gì tôi sẽ chủ ý không xây dựng

- **Một agent, một bộ điều phối, hoặc một vòng lặp thực thi.** mini-SWE-agent đạt điểm >74% trên SWE-bench Verified chỉ với ~200 dòng code và một công cụ bash. Host đã có sẵn một vòng lặp tốt hơn thứ tôi có thể tự viết. Mỗi giờ dành cho phần này là một giờ không dành cho tầng tri thức, vốn là bài toán thực sự chưa có lời giải.
- **Một đồ thị tri thức hoặc một chỉ mục code.** GSD đã xây dựng cả hai và kết thúc với bốn cách biểu diễn khác nhau cho cùng một hệ thống, mỗi thứ đều có câu chuyện lỗi thời riêng. Những mối quan hệ mà bạn không thể kiểm chứng là những gánh nặng nợ nần. Grep, tree-sitter và công cụ phân tích phụ thuộc của hệ sinh thái là đủ dùng cho đến khi các phép đo lường chứng minh điều ngược lại.
- **Các nhân cách của agent.** Năm nhân cách của BMAD chỉ là năm skill đội những chiếc mũ khác nhau. Giá trị nằm ở checklist, không nằm ở vai diễn. Subagent sinh ra là để cô lập ngữ cảnh và chạy song song; đó là lợi ích có thật và nó không cần bất kỳ trò nhập vai nào.
- **Bất kỳ kiểm tra nào triển khai bằng prompt mà có thể viết thành script.** Lệnh `/analyze` của Spec Kit yêu cầu mô hình xây dựng danh mục ID bằng suy luận từ khóa rồi tính toán tỷ lệ bao phủ "một cách xác định". Đó là một lệnh grep. Một nửa vẻ ngoài tinh vi của tài liệu tham chiếu thực chất chỉ là những prompt đang làm tính toán số học một cách vụng về.
- **Tài liệu tự động sinh ra dưới bất kỳ hình thức nào.** Bất cứ thứ gì một lệnh quét có thể tạo ra đều được đưa vào `derived/` dưới dạng JSON kèm nguồn gốc commit, tuyệt đối không đưa vào dưới dạng văn xuôi làm tri thức hệ thống. Kho lưu trữ chỉ chứa những gì code không thể tự nói lên.
- **Một thư viện skill đồ sộ.** Chín skill là mức trần và sáu skill là MVP. 29 skill và 2.4 MB (BMAD) hoặc 44 capabilities và ~90 workflows (GSD) là những gì xảy ra khi framework tăng trưởng nhanh hơn các dự án mà nó phục vụ — và mỗi dòng đều phải trả giá trong mọi phiên làm việc.
- **Một quy trình bootstrap toàn diện ôm đồm.** Mặc định từ chối. Một baseline gồm 8 khái niệm và 6 cạm bẫy, tất cả đều được con người xác nhận, sẽ đánh bại 40 mô tả component được suy diễn tự động, bởi vì tri thức nghe-có-vẻ-đúng-nhưng-thực-ra-sai còn tệ hơn là không có tri thức nào, và sẽ mất tới 6 tháng mới nhận ra cái nào là cái nào.
- **Chỉ số "độ bao phủ tài liệu" (docs coverage).** Nó khuyến khích số lượng và mời gọi sự gian lận. Tỷ lệ `enforced` so với `asserted` mới là con số trung thực.

### Tại sao lại là hình thái này mà không phải các phương án hiển nhiên khác

**Tại sao không phải là "Superpowers cộng thêm một thư mục tri thức hệ thống"?** Bởi vì một thư mục văn xuôi chính xác là những gì GSD đã có, và cơ chế phát hiện độ lệch của nó đã phải lùi bước về `structureMd.includes(prefix)` — so khớp chuỗi con trên markdown tự do — bởi vì văn xuôi không thể kiểm tra tự động được. Định dạng phải thay đổi trước tiên; việc thêm các tài liệu vào một harness hành vi không tạo ra được một tầng tri thức.

**Tại sao không phải là "OpenSpec cộng thêm các ADR"?** Đây là phương án gần nhất trong số 6 dự án, và nó là khung xương mà tôi đang kế thừa. Nhưng tầng vĩnh viễn của OpenSpec chỉ bao gồm các yêu cầu có thể quan sát được từ bên ngoài. Nó không có component, không có hướng phụ thuộc, không có các invariant không quan sát được, không có neo và hoàn toàn không có tín hiệu lỗi thời nào, vì vậy ngay khoảnh khắc code xê dịch bên dưới một requirement thì không có gì phát hiện ra. Việc bổ sung ADR chỉ thêm lý do lập luận chứ không tăng tính kiểm chứng được.

**Tại sao không "chỉ sử dụng các công cụ sẵn có"** — ArchUnit, oasdiff, các ADR trong một thư mục, các bài test đóng vai trò spec? Đây là phương án thay thế mạnh mẽ nhất và nó chiếm phần lớn câu trả lời của tôi. Khoảng trống mà nó để lại là không có gì kết nối các công cụ với lập luận logic: không có một artifact duy nhất nào nói rằng *quy tắc này tồn tại vì quyết định kia, và nó chi phối những component đó, và đây là đặc tính mà nó bảo vệ*. Mô liên kết đó chính là thứ mà một agent cần và là thứ mà một tệp quy tắc không thể mang theo. Claim chính là mô liên kết; các công cụ chính là bộ máy thực thi.

**Tại sao không làm lớn hơn?** Bởi vì tài liệu tham chiếu đồng thuận trên một điểm duy nhất mà không ai dám nói to ra: các dự án có bộ máy cồng kềnh nhất lại có ít bằng chứng nhất cho thấy bộ máy đó giúp ích được gì, và dự án hoàn toàn không có phương pháp luận nào lại công bố những con số thực tế duy nhất. Dưới sự không chắc chắn đó, nước đi đúng đắn là xây dựng thứ nhỏ nhất có thể *sai theo một cách mang lại nhiều thông tin* — và sau đó đo lường nó (Q1, Q2, Q3).

### Phiên bản tóm gọn trong một câu

Xây dựng anchored claim và bộ máy giúp nó có thể kiểm chứng được; kế thừa vòng đời từ OpenSpec và GSD; ủy quyền thực thi cho host agent; từ chối mọi thứ khác cho đến khi các phép đo lường chứng minh điều ngược lại.
