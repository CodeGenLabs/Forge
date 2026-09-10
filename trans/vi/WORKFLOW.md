# WORKFLOW.md — Quy trình làm việc

Vòng đời phát triển. Mọi phase dưới đây đều là một node trong một đồ thị DAG artifact được khai báo (cơ chế của OpenSpec), được kiểm soát bởi các kiểm tra xác định tại các điểm vòng đời có tên (cơ chế của GSD), với tập hợp node bắt buộc được lựa chọn bởi một bộ định tuyến quy mô (cơ chế của Superpowers). Hãy đọc [SYSTEM_KNOWLEDGE.md](SYSTEM_KNOWLEDGE.md) trước — một số phase tồn tại chỉ nhằm phục vụ cho tài liệu đó.

Tên làm việc của công cụ: `forge`.

---

## 0. Hai yếu tố giúp quy trình này có tính thực thi cưỡng chế thay vì chỉ mang tính tư vấn

**DAG là dữ liệu.** File `.forge/schema/<track>.yaml` khai báo các artifact với các trường `id`, `generates`, `requires`, `template`, `instruction`. Thứ tự thực hiện được tính toán bằng thuật toán, không phải hướng dẫn bằng prompt. Trạng thái được phái sinh từ hệ thống tệp — một artifact được coi là hoàn thành khi và chỉ khi đường dẫn trong `generates` của nó tồn tại — vì vậy không có tệp trạng thái nào để mà bị mất đồng bộ.

**Các cổng kiểm soát (gates) là các mã thoát lệnh (exit codes).** Một cổng có dạng `{point, check, blocking, when, onError}`. Lệnh `forge gate <point>` chạy các cổng được đăng ký tại điểm đó và trả về mã thoát khác 0 nếu có một cổng loại chặn (blocking) bị thất bại. Không có bất kỳ điều gì trong vòng đời được thực thi bằng một câu chỉ dẫn mơ hồ bảo mô hình "hãy cẩn thận".

Các điểm đặt cổng: `investigate:pre`, `spec:post`, `impact:post`, `design:post`, `analyze:post`, `tasks:post`, `implement:pre`, `implement:task:post`, `verify:pre`, `verify:post`, `sync:pre`, `converge:post`.

---

## 1. Các Track: Bộ định tuyến quy mô (Scale router)

Việc phân loại diễn ra một lần duy nhất, nói rõ thành lời, ngay khi bắt đầu phase `understand`. Cơ chế bánh cóc là **một chiều (one-way ratchet)**: việc phát hiện sự phức tạp tiềm ẩn sẽ nâng cấp track và được ghi nhận lại; tuyệt đối không có việc hạ cấp track.

| | **Track A — Thăm dò (Probe)** | **Track B — Có giới hạn (Bounded)** | **Track C — Cấu trúc (Structural)** |
|---|---|---|---|
| Khi nào áp dụng | Một câu hỏi, không phải một sản phẩm bàn giao. "Liệu chúng ta có thể…", "có khả thi không…", các bản spike, code thử nghiệm vứt đi | Một thay đổi có phạm vi rõ ràng đối với một luồng **đã tồn tại trong repo này** và không chạm vào bất kỳ claim `ARC-`/`API-`/`DAT-` nào | Hệ thống con hoặc năng lực mới; thay đổi ranh giới component, giao diện công khai, mô hình dữ liệu, một bất biến, hoặc bất kỳ claim `ARC-` nào; hoặc thay đổi nhạy cảm về bảo mật/migration |
| Artifacts bắt buộc | không có (trả lời trong chat) | `proposal.md` (kèm mục nội dòng `## Claims touched`), `spec/` **nếu có thay đổi hành vi**, `tasks.md` | `proposal.md`, `spec/`, `impact.md`, `design.md`, `tasks.md` |
| Các phase chạy | understand, investigate | understand, investigate, spec?, tasks, implement, verify, sync, converge | tất cả các phase |
| Cổng con người duyệt | G1 | G1, G5 | G1, G2, G3, G5, và G4/G6 nếu bị kích hoạt |
| Ngân sách (mặc định) | 15 bước / 10 phút | 60 bước / 45 phút | không giới hạn tổng số bước, áp dụng giới hạn theo từng task |
| Code có giữ lại không | Không — được dán nhãn là đồ bỏ | Có | Có |

**Các yếu tố kích hoạt nâng cấp tự động** (được tính toán bằng máy, không phải phán đoán cảm tính). `forge track check` tự động nâng cấp B→C khi bán kính ảnh hưởng ứng viên giao cắt với bất kỳ claim `ARC-`, `API-`, hoặc `DAT-` nào; khi git diff thêm một public export, một route, hoặc một migration; hoặc khi có `> N` tệp (mặc định 15) nằm trong phạm vi. Nâng cấp A→B/C khi đầu ra của đợt thăm dò muốn được giữ lại trong codebase.

**Rào chắn chống phản khuôn mẫu (Anti-pattern guard), kế thừa từ Superpowers.** Ý nghĩ "nó quá đơn giản để cần một bản spec" tự thân nó chính là tín hiệu cho thấy cần phải chọn track nặng hơn. Thứ co giãn theo sự đơn giản là *kích thước của artifact*, tuyệt đối không phải là *sự phê duyệt*.

---

## 2. Vòng đời thay đổi (The change lifecycle)

```
YÊU CẦU NGƯỜI DÙNG (USER REQUEST)
  │
  ├─ understand ─────► quyết định track + phát biểu lại ý định     [G1 con người]
  │
  ├─ investigate ────► ghi chú điều tra + candidates/              (subagent tươi mới)
  │
  ├─ spec ───────────► changes/NNNN/spec/**  (yêu cầu delta)       [G2 con người, track C]
  │
  ├─ impact ─────────► changes/NNNN/impact.md (giải trình claim)
  │
  ├─ design ─────────► changes/NNNN/design.md  (+ ADR nếu cần)     [G3 con người, track C]
  │
  ├─ analyze ────────► báo cáo phân tích (chỉ đọc, không sửa tệp)
  │
  ├─ tasks ──────────► changes/NNNN/tasks.md
  │
  ├─ implement ──────► code + tests, theo từng task, chuẩn TDD     (subagent tươi mới cho mỗi task)
  │   └─ test được gộp vào chu trình đỏ→xanh của từng task
  │
  ├─ verify ─────────► changes/NNNN/verification.json (bằng chứng)
  │
  ├─ sync ───────────► cập nhật spec vĩnh viễn + claims + derived/ [G5 con người]
  │
  └─ converge ───────► lưu trữ change, sổ cái độ lệch sạch sẽ
```

Hai phase từ phác thảo ban đầu của đề bài được chủ ý không tách thành các tài liệu riêng biệt:

- **`test`** được gộp vào `implement` đóng vai trò là nửa đỏ trong chu trình TDD của từng task. Một artifact `tests.md` riêng biệt mô tả các bài test chưa hề tồn tại chỉ là một kế hoạch cho một kế hoạch; các kịch bản của spec đã mang theo đầy đủ ý định kiểm thử rồi.
- **`verification.md`** được sinh tự động (`verification.json` + bản tóm tắt được render), không tự viết tay. Một báo cáo xác minh viết tay là nơi người ta có thể tùy tiện ghi "mọi test đều pass" mà không thực sự chạy chúng, đó chính là dạng thất bại mà Superpowers phải viết hẳn một skill để ngăn chặn.

`consistency analysis` và `system impact analysis` trong đề bài lần lượt ánh xạ thành `analyze` và `impact`; `knowledge-sync.md` trở thành thao tác lệnh `sync` mang tính xác định thay vì một tài liệu văn bản.

---

## 3. Chi tiết từng Phase

Mỗi phase: mục đích → đầu vào → đầu ra → công cụ → cổng con người duyệt → kiểm tra xác định → kiểm tra bằng LLM → tiêu chí hoàn thành.

---

### 3.1 `understand`

**Mục đích.** Chuyển đổi một yêu cầu thành một ý định được phát biểu rõ ràng, một quyết định chọn track, và một danh sách tường minh những điều chưa biết. Không lập kế hoạch, không khám phá code quá sâu, không viết gì ngoài một phát biểu ngắn gọn.

**Đầu vào.** Yêu cầu của người dùng. Tệp `docs/system/OVERVIEW.md`. Bản *chỉ mục* claim (chỉ gồm ID + tiêu đề một dòng, không lấy phần thân) — đây là mô hình truy xuất đúng lúc (just-in-time retrieval): lấy tên trước, chỉ lấy nội dung khi cần.

**Đầu ra.** Một phát biểu ngắn gọn trong khung chat: người dùng muốn gì, đây là track nào và tại sao, những gì chưa rõ. Đối với track A/B, không ghi gì xuống đĩa. Đối với track C, ghi tệp `changes/NNNN-<slug>/.forge.yaml` (`track`, `created`, `intent`).

**Công cụ.** Không có gì ngoài việc đọc hai tệp nhỏ.

**Cổng con người duyệt — G1 (luôn luôn, trên mọi track).** Người dùng xác nhận ý định được phát biểu lại và track đã chọn. Đây là cổng phổ quát duy nhất và nó rất ngắn: một cái gật đầu, hoặc một sự đính chính. Lý do: lựa chọn track quyết định mọi nghĩa vụ tiếp theo, và chọn sai track là sai lầm đắt giá nhất trong toàn bộ vòng đời.

**Kiểm tra xác định.** Giá trị track phải là một trong A/B/C. Slug là duy nhất và an toàn với hệ thống tệp. Thư mục change chưa từng tồn tại trước đó.

**Kiểm tra bằng LLM.** Yêu cầu có bị mơ hồ theo cách làm thay đổi công việc không? Chỉ hỏi **một** câu hỏi tại một thời điểm, và chỉ hỏi những câu mà một lệnh quét repository không thể trả lời được — yêu cầu người dùng xác nhận một thứ có thể grep được là một khiếm khuyết (quy tắc của BMAD, được tiếp thu nguyên văn).

**Tiêu chí hoàn thành.** Ý định được phát biểu lại và được xác nhận; track được ghi nhận; những điều chưa biết được liệt kê.

---

### 3.2 `investigate`

**Mục đích.** Tìm hiểu sự thật khách quan về các phần của hệ thống mà thay đổi này chạm tới, và chỉ ghi lại những gì không thể phái sinh tự động từ code.

**Đầu vào.** Bản phát biểu ý định. `derived/inventory.json`, `derived/deps.json`, `derived/api-surface.json`. Phần thân của các claim có glob `CMP-` hoặc neo giao cắt với phạm vi dự kiến. Bản thân chính repository.

**Đầu ra.** `changes/NNNN/investigation.md` (track C) hoặc một bản tóm tắt trong chat (track A/B), bao gồm: những gì hiện có hôm nay, các claim liên quan theo ID, tập hợp phụ thuộc ngược, các mâu thuẫn phát hiện được giữa claim và code, và những điểm chưa biết rõ ràng. Bất kỳ phát hiện nào không thể phái sinh mà *chưa* phải là một claim sẽ được đưa vào `docs/system/candidates/<topic>.md` với `status: proposed` và một mức độ `confidence`.

**Công cụ.** grep / glob / tree-sitter thông qua host agent; `forge trace claims --paths <globs>`; `forge drift --paths <globs>`; công cụ phân tích phụ thuộc của hệ sinh thái.

**Cô lập ngữ cảnh.** Chạy dưới dạng một **subagent tươi mới** cho track C, hoặc cho bất kỳ cuộc điều tra nào dự kiến đọc nhiều hơn ~20 tệp. Nó tự ghi tệp đầu ra của riêng mình và chỉ trả về một bản tóm tắt, để toàn bộ nội dung đọc không bao giờ tràn vào ngữ cảnh của phiên làm việc chính (lập luận rẽ nhánh của GSD, được củng cố bởi các phát hiện về mục rữa ngữ cảnh).

**Cổng con người duyệt.** Không có.

**Kiểm tra xác định (`investigate:pre`).** Thư mục `derived/` không bị chậm hơn N commit so với HEAD (mặc định 20) — nếu không lệnh `forge sync derived` phải chạy trước. Đưa ra cảnh báo nếu có bất kỳ claim nào trong phạm vi ở trạng thái `stale` hoặc `missing`, bởi vì việc điều tra dựa trên tri thức chưa kiểm chứng chính là cách độ lệch tiền đề (premise drift) xâm nhập vào một kế hoạch (cổng context-drift của GSD, được tổng quát hóa).

**Kiểm tra bằng LLM.** Có claim hiện có nào bị mâu thuẫn bởi những gì vừa đọc được không? (Các mâu thuẫn tìm thấy ở đây được ghi thêm vào `DRIFT.md` dưới dạng các mục đang mở — chúng là độ lệch được phát hiện thông qua việc đọc, và chúng nhận được cùng sự xử lý 4 phán quyết như độ lệch phát hiện bằng so sánh neo.)

**Tiêu chí hoàn thành.** Mọi điều chưa biết từ `understand` đều được trả lời, được ghi nhận thành một ứng viên kèm độ tin cậy, hoặc được chuyển thành một câu hỏi cho cổng G2. Không có mâu thuẫn claim nào bị bỏ sót mà không ghi nhận.

---

### 3.3 `spec`

**Mục đích.** Nêu rõ những gì hệ thống phải làm sau thay đổi này, dưới dạng các yêu cầu delta (delta requirements) đối chiếu với các spec năng lực vĩnh viễn. Chỉ nói về hành vi — không nói về triển khai code.

**Đầu vào.** Ý định, kết quả điều tra, các spec vĩnh viễn cho các năng lực được nêu trong `proposal.md`, danh sách `rules.spec` của dự án từ `.forge/config.yaml`.

**Đầu ra.** `changes/NNNN/spec/<capability-path>/spec.md` sử dụng ngữ pháp delta đóng (của OpenSpec, được tiếp thu trực tiếp):

```markdown
## ADDED Requirements

### Requirement: REQ-refunds-1 — An operator can refund a settled payment
Hệ thống BẮT BUỘC (SHALL) cho phép hoàn tiền đối với bất kỳ khoản thanh toán nào đã quyết toán lên đến số dư có thể hoàn lại còn lại.

#### Scenario: Hoàn tiền một phần trong phạm vi số dư
- **WHEN** nhân viên hoàn 30 trên khoản thanh toán 100 chưa có lần hoàn tiền nào trước đó
- **THEN** khoản hoàn tiền được quyết toán và số dư có thể hoàn còn lại là 70

#### Scenario: Hoàn tiền vượt quá số dư còn lại
- **WHEN** nhân viên hoàn 80 trên khoản thanh toán 100 đã hoàn trước 30
- **THEN** yêu cầu bị từ chối với lỗi `refund_exceeds_balance` và không có bản ghi sổ cái nào được ghi

## MODIFIED Requirements
...   (nội dung cập nhật đầy đủ, tuyệt đối không dùng đoạn diff chắp vá)

## REMOVED Requirements
### Requirement: REQ-old-4 — …
**Reason**: …
**Migration**: …
```

Cộng với `proposal.md`: **Lý do (Why)** (1–2 câu), **Những gì thay đổi (What changes)** (danh sách gạch đầu dòng, đánh dấu `**BREAKING**`), **Các năng lực (Capabilities)** (mới / chỉnh sửa, theo đường dẫn chính xác hiện có), **Tác động (Impact)** (code bị ảnh hưởng, APIs, deps).

**Công cụ.** `forge spec new <capability>`; `forge check spec`.

**Cổng con người duyệt — G2 (track C; track B chỉ khi spec đưa vào một capability mới).** Người dùng đọc bản delta spec. Lý do: đây là hợp đồng. Mọi thứ ở hạ nguồn đều lập luận từ nó, và một yêu cầu sai lầm sẽ làm lãng phí toàn bộ phần còn lại của vòng đời. Giữ ở mức *một* cổng duy nhất bằng cách biến nó thành nơi duy nhất xác nhận ý định sản phẩm.

**Kiểm tra xác định (`spec:post`).** Tiêu đề requirement khớp ngữ pháp; mọi requirement có ≥1 `#### Scenario:`; scenario dùng chính xác bốn dấu thăng; các câu quy chuẩn dùng SHALL/MUST; ID requirement là duy nhất và ổn định; không còn `[NEEDS CLARIFICATION]`; các khối `MODIFIED` chứa nội dung đầy đủ; các khối `REMOVED` chứa Lý do và Chuyển đổi; các capability mới mang trường `## Purpose` đạt độ dài tối thiểu; **một thay đổi zero-delta sẽ bị từ chối trừ khi `.forge.yaml` đặt `skip_spec: true` kèm lý do** (khuôn mẫu bỏ qua có nêu tên của OpenSpec).

**Kiểm tra bằng LLM.** Mỗi requirement có thể kiểm thử được như văn bản đã viết không? Có hai requirement nào bị trùng lặp hoặc xung đột ý nghĩa không? Có requirement nào mô tả cách triển khai thay vì hành vi quan sát được không? Các kịch bản kiểm thử có đủ để giải tỏa yêu cầu không, hay có trường hợp hiển nhiên nào chưa được bao phủ?

**Tiêu chí hoàn thành.** Mọi kiểm tra xác định đều pass; G2 được ghi nhận; mọi scenario đều là thứ mà một bài test có thể assert được.

---

### 3.4 `impact`

**Mục đích.** Trả lời, trước khi có bất kỳ dòng code nào được viết: thay đổi này chạm vào những gì, và tri thức hệ thống nào bắt buộc phải thay đổi theo. Phase này là nơi cơ chế thực thi cốt lõi của harness vận hành.

**Đầu vào.** Bản spec, kết quả điều tra, `derived/deps.json`, tất cả các claim (chỉ metadata — các neo và glob), phạm vi tệp *dự kiến* từ proposal.

**Đầu ra.** `changes/NNNN/impact.md` (track C; đối với track B đây là mục `## Claims touched` nằm ngay trong `proposal.md`, cùng quy tắc, cùng kiểm tra):

```markdown
## Blast radius
Các tệp trong phạm vi (dự kiến): src/payments/refund.ts, src/payments/ledger.ts, src/web/routes/refunds.ts
Các phụ thuộc ngược (reverse dependents): src/app/checkout.ts, src/reporting/settlement.ts
Components: CMP-payments (chính), CMP-web (rìa)

## Claims touched
### Unaffected
- CMP-orders — không có tệp nào trong phạm vi khớp với glob của nó; vòng đời đơn hàng không bị chạm tới
- CON-capture — từ vựng giữ nguyên
- DAT-4 — quy tắc định danh không đổi; các khoản hoàn tiền gắn vào payment id hiện có

### Updated
- INV-7 — giới hạn trở thành giá trị tích lũy qua các lần hoàn tiền một phần, không phải trên từng lần hoàn riêng lẻ

### New
- API-post-refunds — endpoint công khai mới; bắt buộc phải có hợp đồng giao diện
- INV-12 — một khoản hoàn tiền có tính lũy thừa theo idempotency-key

### At risk
- ARC-3 — một cách triển khai ngây thơ sẽ đọc sổ cái trực tiếp từ tầng domain; thiết kế bắt buộc phải giải quyết điểm này

## Requires ADR
- không có (nếu thiết kế giữ cho việc đọc sổ cái nằm phía sau một port)

## Not covered by tests today
- luồng báo cáo quyết toán (src/reporting/settlement.ts) chưa có integration test; bổ sung một bài test hoặc ghi nhận vào DEBT.md
```

**Công cụ.** `forge impact --change NNNN` tạo ra bán kính ảnh hưởng *ứng viên* và tập hợp chạm-claim *được tính toán*; agent sẽ chọn lọc và hoàn thiện phần văn xuôi. Một nửa do máy tính, một nửa do phán đoán của con người/agent, theo đúng chủ ý thiết kế (mô hình của CodePlan, nhưng không tốn chi phí như CodePlan).

**Cổng con người duyệt.** Không có cổng riêng — các mục `At risk` và `Requires ADR` sẽ là đầu vào cho cổng G3.

**Kiểm tra xác định (`impact:post`).** Mọi thành viên trong tập hợp chạm-claim được tính toán đều phải xuất hiện dưới chính xác một tiêu đề; mọi mục `Superseded` đều phải nêu tên một ADR hiện có; mọi claim `New` đều phải có loại và các neo được đề xuất; các mục `At risk` nêu tên một claim `ARC-`/`API-`/`DAT-` sẽ bắt buộc chuyển sang `track: C`.

**Kiểm tra bằng LLM.** Có lý do biện minh "Unaffected" nào thực sự bị sai không? Có workflow hay consumer nào bị ảnh hưởng mà phân tích phụ thuộc không nhìn thấy không (consumer của hàng đợi message queue, cron job, SDK của client, câu truy vấn dashboard)?

**Tiêu chí hoàn thành.** Tập hợp chạm-claim được giải trình đầy đủ; track được chốt cuối cùng; yêu cầu viết ADR được xác định dứt khoát.

---

### 3.5 `design`

**Mục đích.** Quyết định *cách thức thực hiện (how)*, và ghi lại những quyết định đáng để ghi nhớ. Chỉ dành cho Track C.

**Đầu vào.** Spec, impact, các claim `ARC-`/`CMP-` đang ràng buộc khu vực này, các quy tắc `rules.design` từ config.

**Đầu ra.** `changes/NNNN/design.md` với các phần **Bối cảnh (Context)** (chỉ những gì cần thiết để giải thích phương án; tham chiếu proposal thay vì nhắc lại), **Mục tiêu / Phi mục tiêu (Goals / Non-goals)**, **Các quyết định (Decisions)** (mỗi quyết định kèm các phương án thay thế đã cân nhắc và lý do từ chối), **Rủi ro / Đánh đổi (Risks / Trade-offs)** (`[Rủi ro] → Biện pháp giảm thiểu`), **Kế hoạch chuyển dịch (Migration plan)** (nếu có), **Các câu hỏi mở (Open questions)** (chỉ những câu thực sự có thể hoãn lại).

Cộng thêm, khi `impact.md` yêu cầu: `docs/system/decisions/ADR-NNNN-<slug>.md` — trạng thái, bối cảnh, quyết định, hệ quả, các phương án thay thế, trường `supersedes`, và các ID claim mà nó biện minh.

**Quy tắc phân biệt design.md với một bản ADR:** `design.md` gắn theo từng thay đổi và sẽ bị lưu trữ (archive); một bản ADR mang tính vĩnh viễn. Một quyết định được đưa vào ADR **khi và chỉ khi** một kỹ sư tương lai cần nó để hiểu tại sao mã nguồn lại có hình thái như vậy. Mọi thứ khác nằm lại trong `design.md`. Điều này khắc phục triệt để vấn đề của OpenSpec khi mà lý do lập luận đang sống lại bị chôn vùi trong `changes/archive/*/design.md`.

**Công cụ.** `forge adr new`; `forge check design`.

**Cổng con người duyệt — G3 (track C).** Người dùng phê duyệt phương án tiếp cận và bất kỳ bản ADR nào đi kèm. Lý do: đây là thời điểm cuối cùng mà việc đổi hướng còn ít tốn kém. Trình bày các quyết định kèm các phương án thay thế, không kể lể dông dài.

**Kiểm tra xác định (`design:post`).** Mọi mục trong `Decisions` đều có lý do lập luận và ít nhất một phương án thay thế đã được xem xét; không có placeholder; mọi claim được đánh dấu `Superseded` trong `impact.md` đều có một ADR với trường `supersedes` nêu tên quyết định trước đó; mọi ADR tham chiếu ≥1 ID claim; mục `Open questions` phải rỗng hoặc mỗi câu hỏi phải nêu rõ lý do tại sao nó có thể chờ đợi.

**Kiểm tra bằng LLM.** Bản thiết kế có thỏa mãn mọi yêu cầu trong spec không? Nó có vi phạm claim `ARC-` nào mà `impact.md` chưa gắn cờ không? Có phương án tiếp cận nào đơn giản hơn mà thiết kế chưa xem xét không? Có "câu hỏi mở" nào thực chất là câu hỏi chặn không (câu hỏi làm thay đổi spec, phương án tiếp cận, hoặc việc phân rã task bắt buộc phải được giải quyết ngay, không được hoãn lại)?

**Tiêu chí hoàn thành.** Mọi kiểm tra xác định đều pass; G3 được ghi nhận; không còn claim `At risk` nào chưa được xử lý dứt điểm.

---

### 3.6 `analyze`

**Mục đích.** Kiểm tra tính nhất quán xuyên suốt các artifact, trước khi bắt tay vào triển khai code. **Chế độ chỉ đọc: phase này tuyệt đối không bao giờ chỉnh sửa tệp nào.** (Tiếp thu ràng buộc của Spec Kit.)

**Đầu vào.** Mọi thứ đã được tạo ra từ đầu đến giờ, cộng với hiến chương và kho lưu trữ claim.

**Đầu ra.** Một báo cáo in ra terminal và tệp `changes/NNNN/analysis.md` (bảng phát hiện + bảng bao phủ + các chỉ số). Các phát hiện mang ID ổn định và mức độ nghiêm trọng CRITICAL / HIGH / MEDIUM / LOW. Biện pháp khắc phục chỉ được *đề xuất*, không bao giờ tự động áp dụng.

**Kiểm tra xác định (`analyze:post`) — đây là phần trọng tâm của phase.**

| # | Phép kiểm tra | Mức độ nghiêm trọng |
|---|---|---|
| 1 | Các artifact bắt buộc phải hiện diện đầy đủ theo track đã khai báo | CRITICAL |
| 2 | `requires` của DAG được thỏa mãn cho mọi artifact hiện diện | CRITICAL |
| 3 | Mọi `REQ-*` trong spec được tham chiếu bởi ≥1 task | CRITICAL |
| 4 | Mọi task tham chiếu ≥1 `REQ-*` (hoặc được gắn thẻ `chore`) | HIGH |
| 5 | Tập hợp chạm-claim được giải trình đầy đủ trong `impact.md` | CRITICAL |
| 6 | Quét placeholder trên toàn bộ các artifact của change | HIGH |
| 7 | ID của task là duy nhất và rõ ràng trong các nhóm `## N.` | MEDIUM |
| 8 | Mọi claim bị đánh dấu `Superseded` đều có bản ADR đi kèm | CRITICAL |
| 9 | Các quy tắc hiến chương đã được cơ giới hóa (xem `.forge/config.yaml` `rules`) | CRITICAL |
| 10 | Không có claim nào trong phạm vi ở trạng thái `missing`; các claim `stale` đều xuất hiện trong `impact.md` | HIGH |
| 11 | Mọi tệp được nêu tên trong một task đều tồn tại hoặc được đánh dấu `Create:` | MEDIUM |
| 12 | Các interface được khai báo `Produces:` bởi một task và `Consumes:` bởi một task khác phải khớp về tên và kiểu | HIGH |
| 13 | Các claim `API-` có hợp đồng: tệp hợp đồng được nêu tên và phải hiện diện | HIGH |
| 14 | Có thay đổi mô hình dữ liệu trong phạm vi nhưng thiếu task migration trong danh sách task | HIGH |

**Kiểm tra bằng LLM (mang tính tư vấn, tối đa 20 phát hiện).** Sự lệch pha thuật ngữ giữa các artifact; hai requirement mang cùng một ý nghĩa; một requirement có các scenario không thực sự kiểm chứng được nó; một quan hệ phụ thuộc ngầm về thứ tự giữa các task không được nêu trong kế hoạch; một task mâu thuẫn với nội dung văn xuôi của một claim đang hiệu lực.

**Tiêu chí hoàn thành.** Không còn phát hiện CRITICAL nào. Các phát hiện HIGH được ghi nhận rõ trong một dòng cho mỗi mục. Dưới mức đó, báo cáo chỉ mang tính thông tin.

---

### 3.7 `tasks`

**Mục đích.** Phân rã công việc thành các đơn vị có thể review độc lập và kiểm thử độc lập.

**Đầu vào.** Spec, design, impact, `rules.tasks`.

**Đầu ra.** `changes/NNNN/tasks.md`. Định dạng là định dạng kế hoạch của Superpowers, được thắt chặt bằng các ID:

```markdown
## 2. Refund domain logic

- [ ] 2.1 [REQ-refunds-1, INV-7] Từ chối các khoản hoàn tiền vượt quá số dư còn lại
  **Files:** Sửa `src/payments/refund.ts#computeRefundable`; Test `tests/payments/refund.spec.ts`
  **Consumes:** `Payment.capturedAmount: Money`, `Refund.settledTotal(paymentId): Money`
  **Produces:** `computeRefundable(payment: Payment, settled: Money): Money`
  **Verify:** `pnpm test tests/payments/refund.spec.ts` — trường hợp mới fail trước khi sửa, pass sau khi sửa
  - [ ] viết bài test failing (code nguyên văn bên dưới)
  - [ ] chạy test, xác nhận nó fail với thông điệp mong đợi
  - [ ] triển khai code tối thiểu
  - [ ] chạy lại test, xác nhận pass; chạy toàn bộ suite của tệp đó
  - [ ] commit
```

Các quy tắc mang tính xác định: mọi task mang thẻ `[REQ-*]`/`[INV-*]`; mọi task nêu đường dẫn tệp chính xác; mọi task nêu lệnh verify và bước chuyển trạng thái dự kiến; các interface được khai báo với chữ ký thực tế; **không có placeholder** — những câu như "thêm xử lý lỗi thích hợp", "TBD", "tương tự task N", "viết test cho phần trên" mà không có code test nguyên văn đều bị từ chối thẳng thừng.

**Quy mô task chuẩn xác (Task right-sizing)** (tiếp thu từ Superpowers): một task là đơn vị nhỏ nhất mang theo chu trình test riêng của nó và xứng đáng để một reviewer mới tinh duyệt qua. Gộp phần cài đặt setup và tài liệu vào chính task mà sản phẩm của nó cần tới chúng. Chỉ tách task ở nơi mà reviewer có thể từ chối một task trong khi vẫn phê duyệt task bên cạnh.

**Cổng con người duyệt.** Không có. Nếu các task bị sai, lệnh `analyze` hoặc đợt review theo từng task sẽ bắt được, và cổng G3 đã phê duyệt phương án tiếp cận trước đó rồi.

**Kiểm tra xác định (`tasks:post`).** Toàn bộ các quy tắc trên; cộng thêm mọi `REQ-*` đều được bao phủ; tính nhất quán `Produces`/`Consumes` giữa các task (kiểm tra số 12 ở trên); cộng thêm bắt buộc phải có task thay đổi schema nếu mô hình dữ liệu nằm trong phạm vi (cổng schema của GSD, được chuyển lên sớm hơn để nó trở thành một thất bại khi lập kế hoạch thay vì một sự bất ngờ khó chịu khi xác minh).

**Kiểm tra bằng LLM.** Có task nào đang làm hai việc cùng lúc không? Thứ tự thực hiện có thực sự bị ép buộc bởi quan hệ phụ thuộc hay chỉ là liệt kê tùy tiện? Một kỹ sư mới toanh không có ngữ cảnh trước đó liệu có thể thực thi task N chỉ từ nội dung văn bản của nó không?

**Tiêu chí hoàn thành.** Mọi kiểm tra đều pass; mọi requirement được bao phủ; không có placeholder.

---

### 3.8 `implement`

**Mục đích.** Biến các task thành code, ưu tiên viết test trước (test-first), thực hiện từng task một.

**Đầu vào.** Một task đơn lẻ, cộng với các interface `Consumes` được khai báo của nó, cộng với các claim trong tập chạm cho các tệp của task đó, cộng với quy ước dự án. **Tuyệt đối không** nạp toàn bộ change, không nạp lịch sử phiên làm việc trước đó.

**Đầu ra.** Code, tests, một commit cho mỗi task, các ô checkbox được tích chọn.

**Mô hình thực thi.** Subagent tươi mới cho mỗi task (Superpowers). Subagent nhận một bản tóm lược nhiệm vụ được tự động cấu trúc — nội dung task, phạm vi tệp được phép chạm, các claim cụ thể và văn xuôi của chúng, lệnh verify — và trả về một git diff cùng đầu ra của lệnh verify. Phiên điều phối chính chỉ lưu giữ sổ cái. Các ngân sách được thực thi bằng mã nguồn (mini-SWE-agent): giới hạn số bước cho mỗi task, giới hạn thời gian thực (wall-time), và giới hạn số lần thất bại liên tiếp; quỹ đạo thực thi được ghi vào `changes/NNNN/trajectories/<task>.json` ở mỗi bước.

**Chu trình TDD, không thể thương lượng bên trong một task.**

```
viết bài test thất bại  →  CHẠY NÓ, QUAN SÁT NÓ FAIL  →  triển khai code tối thiểu
       →  CHẠY NÓ, QUAN SÁT NÓ PASS  →  chạy suite của tệp  →  refactor nếu cần  →  commit
```

Bước thứ hai là bước hay bị bỏ qua nhất và là bước quan trọng nhất: một bài test mà bạn chưa từng chứng kiến nó fail thì không phải là bằng chứng, nó chỉ là đồ trang trí. Cổng `implement:task:post` ghi nhận đầu ra đỏ và xanh đã quan sát được vào trajectory, và `verify` sẽ đối chiếu chéo xem cả hai có tồn tại cho mọi task được gắn thẻ claim `INV-` hay không.

**Rào chắn ở cấp độ công cụ, không phải ở cấp độ prompt** (cơ chế của SWE-agent). Nếu hệ sinh thái hỗ trợ: chạy linter/parser trước và sau khi sửa code và tự động revert việc sửa đổi nếu xuất hiện lỗi cú pháp mới, trả về thông điệp lỗi cho agent. Từ chối mọi chỉnh sửa nằm ngoài phạm vi tệp được khai báo của task.

**Cổng con người duyệt.** Không có cổng giữa các task. Superpowers rất đúng khi cho rằng một kế hoạch đang chạy không nên dừng lại chờ con người; các xung đột, điểm mơ hồ và khiếm khuyết của kế hoạch phải được quyết định và ghi nhận lại, không được xếp hàng chờ. **Ngoại trừ** hai điểm dừng khẩn cấp ở §4: một đợt migration có tính hủy diệt dữ liệu và một quyết định nhạy cảm về bảo mật sẽ lập tức dừng lại bất kể chúng xuất hiện ở đâu.

**Kiểm tra xác định.** `implement:pre`: cây thư mục làm việc sạch sẽ, đang ở trên một branch/worktree, `derived/` tươi mới, `analyze` đã pass. `implement:task:post`: lệnh verify của task trả về mã thoát 0; diff chỉ chạm vào các tệp đã khai báo; các tệp test mới/thay đổi mang thẻ `@covers` cho các ID requirement của task; commit message có tham chiếu ID của task.

**Kiểm tra bằng LLM (theo từng task, review hai giai đoạn — Superpowers).** Giai đoạn 1: git diff có thỏa mãn requirement của task và chỉ requirement đó không? Giai đoạn 2: chất lượng code có chấp nhận được không — cách đặt tên, trùng lặp code, xử lý lỗi, tính nhất quán với các quy ước xung quanh? Cả hai giai đoạn đều do một subagent reviewer chưa từng tham gia viết code thực hiện.

**Tiêu chí hoàn thành.** Mọi task được tích chọn hoàn thành; việc xác minh của mọi task đã được quan sát trực tiếp; các đợt review theo task đã pass hoặc các phát hiện đã được chuyển thành các task bổ sung tiếp theo.

---

### 3.9 `verify`

**Mục đích.** Tạo ra bằng chứng xác thực rằng thay đổi đã hoàn tất. Không phải là một ý kiến cảm tính — mà là một artifact cụ thể.

**Đầu vào.** Toàn bộ cây thư mục làm việc, bản spec, kho lưu trữ claim, thư mục `derived/`.

**Đầu ra.** Tệp `changes/NNNN/verification.json` cộng với bản tóm tắt được render. Được sinh tự động, tuyệt đối không viết tay.

```json
{
  "change": "0004-refund-support",
  "commit": "f7e8d9a",
  "generated_at": "2026-09-10T13:22:41Z",
  "gates": {
    "build":            {"status": "pass", "cmd": "pnpm build", "exit": 0},
    "typecheck":        {"status": "pass", "cmd": "pnpm typecheck", "exit": 0},
    "lint":             {"status": "pass", "cmd": "pnpm lint", "exit": 0},
    "tests":            {"status": "pass", "cmd": "pnpm test", "passed": 412, "failed": 0, "skipped": 3},
    "arch_rules":       {"status": "pass", "cmd": "depcruise --config .forge/rules/deps.cjs", "exit": 0},
    "contract_diff":    {"status": "pass", "tool": "oasdiff", "breaking": 0, "non_breaking": 2},
    "requirement_cover":{"status": "pass", "requirements": 5, "discharged": 5, "undischarged": []},
    "claim_evidence":   {"status": "pass", "enforced_claims": 19, "failing": []},
    "drift":            {"status": "pass", "open": 0, "waived": 0},
    "debt":             {"status": "pass", "open": 0, "waived": 1},
    "derived_fresh":    {"status": "pass", "commits_behind": 0}
  },
  "verdict": "pass"
}
```

**Định nghĩa hoàn thành (Definition of done).** Kết quả `verdict: pass` bắt buộc phải thỏa mãn **tất cả** các điều kiện sau:

1. build, typecheck, lint, toàn bộ bộ test suite đều xanh — với đầu ra tươi mới được capture trực tiếp tại đây, không phải từ trí nhớ;
2. mọi `REQ-*` trong change này được giải tỏa bởi ≥1 test pass mang thẻ `@covers` của nó;
3. mọi claim `enforced` trong tập chạm vẫn được chứng minh bởi bằng chứng của nó (các rule pass, contract diff nằm trong ngưỡng cho phép, các invariant test pass);
4. bản giải trình chạm-claim trong `impact.md` là đầy đủ trọn vẹn;
5. `DRIFT.md` không có mục mở nào chưa được miễn trừ chạm vào các claim của change này;
6. `DEBT.md` không có mục mở nào chưa được miễn trừ do chính change này tạo ra — các hàm stub, các chữ `TODO` được thêm bởi change, các test bị skip, các lần xác minh chưa chạy (tiếp thu `broken-windows` của GSD);
7. `derived/` tạo lại thành no-op (không có thay đổi) tại commit này;
8. không có bài test nào bị skip mà vốn đã pass trước khi có change này.

**Tests pass chỉ là điều kiện 1 trong 8 điều kiện.** Đó là câu trả lời cụ thể cho yêu cầu của bản tóm lược nhiệm vụ rằng harness không được phép tuyên bố thành công chỉ vì tests pass.

**Các trường hợp miễn trừ (Waivers).** Mục 5 hoặc 6 có thể được miễn trừ bằng cờ `--reason` kèm thời hạn hết hạn; quyền miễn trừ sẽ xuất hiện trong `verification.json` và trong `forge status`. Các điều kiện 1–4 và 7 tuyệt đối không thể miễn trừ.

**Cổng con người duyệt.** Không có — phase này hoàn toàn mang tính cơ học. *Đầu ra* của nó sẽ là dữ liệu cho cổng G5.

**Kiểm tra bằng LLM.** Một đợt review tổng thể toàn bộ change đối chiếu lại với spec (giai đoạn review thứ ba): tổng hòa của các task có thực sự mang lại các yêu cầu đề ra không, và có điều gì bị lệch pha xuyên qua ranh giới giữa các task không?

**Tiêu chí hoàn thành.** `verdict: pass`, hoặc có một sự miễn trừ được ghi nhận rõ ràng.

---

### 3.10 `sync`

**Mục đích.** Đưa những gì thay đổi này đã xác lập vào tri thức vĩnh viễn, một cách xác định.

**Đầu vào.** `verification.json` (bắt buộc phải là `pass`), các spec delta, `impact.md`, cây thư mục làm việc.

**Đầu ra.** Các spec năng lực vĩnh viễn được cập nhật; các claim được cập nhật/tạo mới/hủy bỏ; các commit SHA của anchor được tịnh tiến; thư mục `derived/` được tạo lại; các mục trong `DRIFT.md` được ghi thêm nếu có phát hiện mới.

**Các thao tác tuần tự, từ chối ngay ở thất bại đầu tiên** (chi tiết trong mục §9.3 của [SYSTEM_KNOWLEDGE.md](SYSTEM_KNOWLEDGE.md)):

1. gập các bản delta spec vào các spec vĩnh viễn (hợp nhất xác định ADDED/MODIFIED/REMOVED/RENAMED, kèm xác thực trước khi ghi của spec được dựng lại);
2. xác minh mọi chỉnh sửa claim trong git diff đều có mục tương ứng trong `impact.md` và, nếu cần, có bản ADR đi kèm;
3. neo lại `@sha` của mọi claim bị chạm vào commit merge — **đây là con đường duy nhất để mốc "verified as of" tiến về phía trước**;
4. tạo lại `derived/` và `trace.json`;
5. chạy lại `forge drift` và ghi thêm các phát hiện mới vào trạng thái open;
6. từ chối thực hiện nếu bất kỳ điều kiện từ chối nào trong §9.3 bị vi phạm.

**Cổng con người duyệt — G5 (mọi track tạo ra artifact).** Người dùng phê duyệt biến động tri thức (knowledge delta), được hiển thị dưới dạng diff nguyên văn của kho lưu trữ claim cộng với bản spec đã gập, bên cạnh một dòng sổ cái cho mỗi claim (`retain / rewrite / new / retire`, kèm lý do). Không phải là bản tóm tắt — mà là văn bản thực tế. Lý do: đây là thao tác ghi duy nhất sống sót sau khi change kết thúc, và giao thức xác-nhận-trước-khi-lưu của OpenHands cùng sổ cái của BMAD là hai chính sách được lập luận cẩn trọng nhất trong tài liệu tham chiếu. Một lần tương tác duy nhất; đòn bẩy kiểm soát rất cao.

**Kiểm tra xác định (`sync:pre`).** `verification.json` là `pass` và commit của nó khớp với HEAD; kho lưu trữ vượt qua toàn bộ kiểm định của §7 sau khi gập; ngân sách số dòng nạp-liên-tục vẫn được đảm bảo.

**Kiểm tra bằng LLM.** Đối với mỗi claim mới được đề xuất: nó có thỏa mãn tiêu chí kết nạp không — một kỹ sư có năng lực có thể đọc ra nó từ mã nguồn chuẩn mực không? Nếu có, nó là thông tin phái sinh và không được phép lưu trữ.

**Tiêu chí hoàn thành.** Kho lưu trữ hợp lệ; G5 được ghi nhận; các neo được tịnh tiến SHA.

---

### 3.11 `converge`

**Mục đích.** Đóng thay đổi và để repository ở trạng thái sẵn sàng để thay đổi tiếp theo bắt đầu sạch sẽ.

**Đầu vào.** Một change đã được đồng bộ hoàn tất (synced change).

**Đầu ra.** Thư mục `changes/archive/YYYY-MM-DD-<slug>/` chứa mọi artifact bao gồm `verification.json` và các file trajectory. Branch được merge hoặc PR được mở. Lệnh `forge status` sạch sẽ.

**Kiểm tra xác định (`converge:post`).** Mọi task đã được tích chọn; việc di chuyển vào archive đã hoàn tất và thư mục đang hoạt động đã biến mất; bản archive đồng nhất từng byte với những gì đã được xác minh; các mục mở trong `DRIFT.md` đều có phán quyết hoặc miễn trừ; lệnh `forge check` vượt qua trên toàn bộ repository tại commit merge.

**Kiểm tra bằng LLM.** Không có. Convergence thuần túy là việc sổ sách quản trị.

**Tiêu chí hoàn thành.** Đã lưu trữ; repository xanh; các mục còn mở đều đã được giải quyết hoặc được mang theo rõ ràng kèm lý do được ghi nhận.

---

## 4. Các cổng do con người duyệt: Danh sách hoàn chỉnh

Chính xác là sáu cổng. Mọi thứ khác đều là quyết định của agent. Danh sách này là câu trả lời của harness cho yêu cầu "harness KHÔNG ĐƯỢC hỏi những câu hỏi thừa thãi": cách để giành được quyền chạy tự động không cần giám sát trong một giờ là phải cực kỳ chính xác về số ít khoảnh khắc mà sai lầm sẽ rất đắt giá và không thể đảo ngược.

| Cổng | Khi nào | Những gì được hiển thị | Tại sao không thể tự động hóa |
|---|---|---|---|
| **G1 — Ý định & track** | Luôn luôn, khi bắt đầu mỗi yêu cầu | Một đoạn văn: phát biểu lại ý định, track đã chọn, những gì chưa biết | Ý định sản phẩm không nằm trong repository. Lựa chọn track thiết lập mọi nghĩa vụ phía sau |
| **G2 — Spec** | Track C; track B khi xuất hiện một năng lực mới | Các yêu cầu delta và các kịch bản kiểm thử | Spec là hợp đồng; một yêu cầu sai sẽ làm lãng phí toàn bộ vòng đời |
| **G3 — Thiết kế & ADR** | Track C | Các quyết định kèm phương án thay thế, rủi ro, và bản ADR | Thời điểm cuối cùng việc đổi hướng còn ít tốn kém; một ADR là một cam kết mà con người nên đưa ra |
| **G4 — Thao tác rủi ro cao** | Bất cứ khi nào phát hiện, trên mọi track, ngay lập tức | Thao tác chính xác và bán kính ảnh hưởng của nó | Migration phá hủy dữ liệu, xóa dữ liệu, đổi chứng chỉ/quyền hạn, dependency có loại giấy phép mới, bất cứ thứ gì chạm vào auth. Không thể đảo ngược hoặc liên quan đến bảo mật |
| **G5 — Biến động tri thức** | Bất kỳ change nào tạo ra artifact | Diff nguyên văn của kho claim + spec đã gập + một dòng sổ cái cho mỗi claim | Thao tác ghi này sống lâu hơn change. Ghi tri thức không qua review là cách các kho lưu biến thành đống rác nhiễu |
| **G6 — Phán quyết độ lệch** | Bất cứ khi nào phát hiện độ lệch trên một claim trụ cột | Claim bị lỗi thời, diff của fingerprint, phán quyết được đề xuất và lập luận | arXiv:2604.03447: mô hình yếu nhất một cách có hệ thống tại điểm này và độ tự tin của nó không có giá trị phân biệt |

**Tính tự chủ lũy tiến (Progressive autonomy).** File `.forge/config.yaml` mang cấp độ `autonomy` cho từng cổng, và cấp độ này *được tích lũy theo từng dự án*, không phải theo sở thích nhất thời của người dùng:

```yaml
autonomy:
  G1: always            # không bao giờ tự động hóa
  G2: always            # không bao giờ tự động hóa
  G3: always            # nới lỏng thành `track-c-only` sau 20 thay đổi mà không có lần đảo ngược G3 nào
  G4: always            # không bao giờ tự động hóa
  G5: always            # nới lỏng thành `claims-changed-only` (bỏ qua khi chỉ gập spec)
  G6: always            # không bao giờ tự động hóa
  per_task_review: auto # review bằng LLM, không cần con người
```

Chỉ có G3 và G5 là có thể được nới lỏng, và việc nới lỏng là một thay đổi cấu hình được ghi nhận kèm lý do, không phải là sự buông lỏng thói quen. G1, G2, G4 và G6 vĩnh viễn là thủ công — hai cổng đầu vì ý định không nằm trong repository, hai cổng sau vì cái giá của sự sai sót là vô hạn và khả năng phán đoán của mô hình đã được chứng minh là rất yếu.

---

## 5. Quy trình `bootstrap`

Dành cho một repository hiện có chưa từng cài đặt harness. Đây là nơi sự trung thực quan trọng nhất: một LLM đọc một codebase xa lạ sẽ đưa ra các khẳng định đầy tự tin, nghe có vẻ hợp lý nhưng lại sai một phần, và tri thức nghe-có-vẻ-đúng-nhưng-thực-ra-sai còn tệ hơn việc không có tri thức nào.

### 5.1 Những gì có thể tự động hóa một cách thực tế

| Bước | Có thể tự động hóa? | Bằng cách nào |
|---|---|---|
| Quét repository, kiểm kê tệp, số dòng LOC, ngôn ngữ | **100%** | git + globs |
| Phát hiện stack công nghệ và các phiên bản ghim | **100%** | lockfiles, manifests |
| Phát hiện các điểm nhập (entry points) | **~90%** | `bin`/`main`/`scripts` trong manifest, quy ước framework |
| Phát hiện các module / packages | **~90%** | workspace manifests, quy ước thư mục |
| Phát hiện đồ thị phụ thuộc và các chu trình | **100%** nơi có công cụ hệ sinh thái | dependency-cruiser / tach / go list / cargo |
| Phát hiện bề mặt API được export | **~85%** | tree-sitter + quy ước export; route HTTP phụ thuộc framework |
| Phát hiện mô hình dữ liệu | **~70%** | tệp ORM schema, thư mục migration; SQL thuần khó hơn |
| Phát hiện tests, runner, độ bao phủ | **~95%** | tệp config + cờ `--list` của runner |
| Phát hiện các quy ước (đặt tên, định dạng) | **~80%** | config của formatter/linter là chuẩn tắc; phần còn lại lấy mẫu |
| **Suy luận kiến trúc (components, ranh giới, trách nhiệm)** | **~40%** | cấu trúc thư mục + cụm phụ thuộc gợi ý; đặt tên và trách nhiệm đòi hỏi phán đoán |
| **Suy luận các bất biến (invariants)** | **~25%** | code xác thực, assertions, tên test gợi ý; một đặc tính là *bắt buộc* hay chỉ là *tạm thời hiện tại* không nằm trong code |
| **Suy luận các quyết định kiến trúc và lý do lập luận** | **~5%** | thực sự không nằm trong code. Lịch sử git và mô tả PR thỉnh thoảng giúp ích; phần lớn phải phỏng vấn hoặc để trống |
| **Suy luận các cạm bẫy (pitfalls)** | **0%** ban đầu | tích lũy từ các thất bại quan sát được qua thời gian, không thể có từ một lần quét |

**Đây là bảng đánh giá trung thực mà bản tóm lược nhiệm vụ đòi hỏi.** Mọi thứ phía trên các hàng in đậm đều là dữ liệu phái sinh và không bao giờ được trở thành một claim được lưu trữ. Mọi thứ trong các hàng in đậm là việc sinh ứng viên với mức trần thấp, và hai hàng cuối cùng về cơ bản là không thể tự động hóa. Một quy trình bootstrap đưa ra 200 claim đầy tự tin về kiến trúc và bất biến thực chất đang tạo ra chính mớ tiếng ồn mà harness này sinh ra để ngăn chặn.

### 5.2 Ba lượt duyệt (The three passes)

**Lượt 1 — Phái sinh (không dùng LLM, không tạo claim).**
Lệnh `forge bootstrap derive` tạo ra toàn bộ thư mục `derived/` và in ra một bản tóm tắt thực tế khách quan. Mang tính xác định, có thể chạy lại bất cứ lúc nào, và nó bao trọn toàn bộ nửa "phát hiện stack / modules / dependencies / APIs / tests" trong phác thảo bootstrap của đề bài. Không có gì ở đây là tri thức; không có gì ở đây cần phải review.

**Lượt 2 — Đề xuất ứng viên (dùng LLM, rẽ nhánh song song, có giới hạn trần).**
Các subagent song song, mỗi subagent cho một chủ đề (components, domain, invariants, interfaces, data, workflows, strategy, constraints), mỗi con đọc `derived/` cộng với code trong khu vực của nó và tự ghi trực tiếp vào `docs/system/candidates/<topic>.md` — không bao giờ trả nội dung về bộ điều phối (lập luận rẽ nhánh của GSD). Mỗi ứng viên mang theo `status: proposed`, mức `confidence`, các neo, và **bằng chứng mà nó được suy luận từ đó**. Có các mức trần cứng theo từng chủ đề và tổng số (mặc định: tối đa 40 ứng viên tổng cộng), và mỗi agent cũng phải tạo ra một mục `## Uncertain` nêu rõ những gì nó không thể xác định chắc chắn — vốn là phần giá trị nhất trong đầu ra của nó.

Các quy tắc cho việc sinh ứng viên, được thực thi bởi `forge check candidates`:

- Bắt buộc phải có neo. Một ứng viên không có neo sẽ bị loại bỏ.
- Áp dụng tiêu chí kết nạp: nếu văn bản chỉ là sự nhắc lại đoạn code được neo, nó sẽ bị loại bỏ bởi linter phát hiện claim có thể phái sinh (§7.3 của SYSTEM_KNOWLEDGE.md).
- **Không tự bịa ra lý do lập luận.** Một ứng viên không được phép chứa từ "bởi vì" nếu không có bằng chứng cụ thể. Lý do bị thiếu sẽ được ghi là `rationale: unknown`, và nó trở thành một câu hỏi phỏng vấn.
- Các invariant phải nêu tên đoạn code thực thi chúng hoặc bài test chứng minh chúng; một invariant không có cả hai sẽ bị hạ cấp thành một câu hỏi.

**Lượt 3 — Phê chuẩn (con người, dạng phỏng vấn, quy mô nhỏ).**
Lệnh `forge bootstrap review` duyệt qua các ứng viên **theo thứ tự loại có giá trị cao nhất trước** — các cạm bẫy và khái niệm trước các component — và với mỗi mục sẽ hỏi một trong các lựa chọn: phê chuẩn (ratify) / sửa (edit) / từ chối (reject) / hoãn lại (defer). Lồng ghép với các câu hỏi `Uncertain`, theo từng nhóm tối đa tám mục (quy tắc của BMAD), và **tuyệt đối không bao giờ hỏi bất cứ điều gì mà một lệnh quét có thể trả lời**.

Tư thế mặc định là **từ chối**. Sự đầy đủ của baseline không phải là mục tiêu; sự *đáng tin cậy* của baseline mới là mục tiêu. Một baseline gồm 12 claim được phê chuẩn cộng với một tầng `derived/` hoàn chỉnh là một kết quả tốt. Một baseline gồm 40 claim mới chỉ được kiểm tra nửa vời là một món nợ nguy hiểm sẽ bị phát hiện ra sáu tháng sau đó khi một trong số chúng bị sai.

### 5.3 Thiết lập Baseline

Lệnh `forge bootstrap seal` sẽ ghi:

- `docs/system/OVERVIEW.md` — một trang duy nhất, do con người viết hoặc con người phê duyệt, luôn luôn được nạp;
- các claim đã được phê chuẩn trong các tệp theo loại của chúng, các neo được đóng dấu với commit SHA hiện tại, `reviewed` = hôm nay;
- `docs/system/decisions/ADR-0001-adopt-forge.md` — ghi nhận chính bản baseline: những gì đã được phê chuẩn, những gì đã chủ ý không phê chuẩn, và mức trần claim đang có hiệu lực. Điều này làm cho sự *vắng mặt* của tri thức trở nên minh bạch thay vì mơ hồ;
- các ứng viên chưa được phê chuẩn được giữ nguyên vị trí, có thể đọc nhưng không thể trích dẫn làm căn cứ;
- `.forge/config.yaml` với các lệnh công cụ đã phát hiện (build, test, lint, typecheck, dep-rule).

**Phi mục tiêu tường minh của bootstrap:** tạo ra một bản mô tả hoàn chỉnh về toàn bộ hệ thống. Thay đổi đầu tiên chạm vào một khu vực sẽ tạo ra tri thức tốt hơn về khu vực đó so với bất kỳ lệnh quét nào, bởi vì thay đổi đó có một lý do, một bài test, và một con người thực sự quan tâm. Nhiệm vụ của bootstrap là làm cho thay đổi đầu tiên trở nên *khả thi*, không phải là ôm đồm một dự án tài liệu hóa khổng lồ ngay từ đầu.

---

## 6. Các workflow khác

Cùng một bộ máy phase, chỉ khác nhau về tập hợp các node bắt buộc. Mỗi workflow là một file `.forge/schema/<name>.yaml`, không phải viết thêm code mới.

| Workflow | Track | DAG | Ghi chú |
|---|---|---|---|
| **bugfix** | B (C nếu có claim bị liên đới) | understand → **reproduce** → investigate → tasks → implement → verify → sync → converge | `reproduce` là một artifact bắt buộc: một bài test thất bại chứng minh sự tồn tại của bug, được commit trước bất kỳ sửa đổi nào. Không có nguyên nhân gốc rễ thì không sửa lỗi — tín hiệu phương pháp luận mạnh mẽ nhất trong tài liệu tham chiếu (`systematic-debugging` của Superpowers + workflow của mini-SWE-agent đồng thuận). Nếu bug làm lộ ra một bất biến bị vi phạm, bản sửa lỗi sẽ cập nhật bằng chứng của `INV-` thay vì chỉ sửa code |
| **refactor** | B hoặc C | understand → investigate → impact → tasks → implement → verify → sync → converge | `skip_spec: true` là trường hợp bình thường (hành vi không được phép thay đổi), được ghi nhận kèm lý do. Việc xác minh đòi hỏi thêm: không có tệp test nào bị sửa đổi về ngữ nghĩa, và bộ test suite hiện có phải xanh hoàn toàn. `impact` vẫn chạy — tái cấu trúc là nguồn gây ra độ lệch kiến trúc âm thầm có rủi ro cao nhất |
| **architecture-change** | C, luôn luôn | understand → investigate → **ADR** → impact → design → analyze → tasks → implement → verify → sync → converge | Bản ADR xuất hiện *trước* impact, bởi vì bản thân quyết định chính là thứ đang được đưa ra. Đòi hỏi phải cập nhật claim `ARC-` và tệp quy tắc của nó trong cùng một change; `verify` từ chối nếu quy tắc bị nới lỏng mà không có sự giải thích trong ADR |
| **knowledge-only** | B | understand → **claims** → verify → sync → converge | Dùng để thêm một cạm bẫy, một khái niệm, hoặc một ADR mà không có thay đổi code. `verify` chỉ chạy phần kiểm định kho lưu trữ. Quy trình này tồn tại để việc ghi lại tri thức không bao giờ bị chặn vì lý do phải có một đợt sửa code đi kèm |
| **drift-resolution** | B hoặc C | understand → investigate → verdict → (tasks → implement → verify) → sync | Điểm nhập là lệnh `forge drift resolve`. Phán quyết V1 tiếp tục đi vào phần triển khai; V2/V3/V4 có thể kết thúc ngay tại bước sync |

---

## 7. Quản lý ngữ cảnh xuyên suốt các Phase

Đồ thị DAG mang theo hợp đồng ngữ cảnh. Mỗi node artifact khai báo những gì mà phase của nó được phép đọc, vì vậy ngữ cảnh được định phạm vi bởi mô hình dữ liệu thay vì dựa vào tính kỷ luật tự giác.

```yaml
- id: design
  generates: design.md
  requires: [spec, impact]
  reads:
    - changes/${change}/spec/**
    - changes/${change}/impact.md
    - docs/system/architecture.md
    - docs/system/components.md
    - claims: "${impact.claims_touched}"     # được phân giải thành nội dung cụ thể của từng claim
  instruction: |
    ...
```

Lệnh `forge instructions design --change NNNN --json` trả về danh sách tệp đã phân giải và câu chỉ dẫn, để một phase (hoặc một subagent chạy nó) chỉ nạp chính xác ngần đó và không có gì khác — cơ chế `contextFiles` của OpenSpec, được mở rộng với khả năng phân giải ở cấp độ claim.

| Phase | Chiến lược ngữ cảnh |
|---|---|
| understand | Tối thiểu: OVERVIEW + *chỉ mục* claim (chỉ ID và tiêu đề). Tuyệt đối không nạp phần thân claim |
| investigate | **Subagent tươi mới.** Đọc rộng, tự ghi tệp riêng, trả về bản tóm tắt. Phiên làm việc chính không bao giờ nhìn thấy nội dung đọc thô |
| spec | Các delta spec + các spec vĩnh viễn chỉ cho các capability được nêu tên |
| impact | *Metadata* của claim (anchors, globs) + `deps.json`. Không nạp phần thân claim — tập chạm được tính toán từ metadata |
| design | Spec + impact + phần thân cụ thể của các claim trong tập chạm |
| analyze | Toàn bộ artifact của change, nạp một lần, chỉ xuất các phát hiện ra. Chế độ chỉ đọc |
| tasks | Spec + design + impact |
| implement | **Subagent tươi mới cho mỗi task.** Một task, các interface của nó, các claim của nó, phạm vi tệp của nó. Không có gì khác |
| verify | Hoàn toàn không dùng ngữ cảnh mô hình cho phần xác minh xác định; subagent review cuối cùng nhận diff và spec |
| sync | Chỉ nạp bản diff của tri thức |

**Ngân sách** (cơ chế của mini-SWE-agent, được thực thi bằng mã nguồn): theo từng phase và từng task —
`step_limit`, `wall_time_limit_seconds`, `cost_limit`, `max_consecutive_failures`. Vượt quá ngân sách sẽ kết thúc phase kèm lý do được ghi nhận và quỹ đạo được lưu vết, tuyệt đối không có việc âm thầm chạy tiếp.

**Ngân sách nạp-liên-tục (Always-loaded budget):** `OVERVIEW.md` + các tệp claim bắt buộc ≤ 400 dòng (có thể cấu hình). Vượt quá ngân sách là một lỗi mà cách khắc phục hợp lệ duy nhất là cắt giảm bớt claim hoặc chuyển nó ra sau một điều kiện kích hoạt. Ngân sách tuyệt đối không bao giờ được tự ý tăng lên — quy tắc đó đã được ghi rõ trong [CONSTITUTION.md](CONSTITUTION.md).
