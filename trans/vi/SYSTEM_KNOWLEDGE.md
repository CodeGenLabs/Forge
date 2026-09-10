# SYSTEM_KNOWLEDGE.md — Tri thức hệ thống

Bản thiết kế của tầng Tri thức Hệ thống (System Knowledge). Đây là tài liệu trụ cột (load-bearing document) của toàn bộ đề xuất; vòng đời trong [WORKFLOW.md](WORKFLOW.md) và các thành phần trong [ARCHITECTURE.md](ARCHITECTURE.md) tồn tại là để phục vụ nó. Bằng chứng thực nghiệm cho mọi quan điểm được nêu ở đây đều nằm trong [RESEARCH.md](RESEARCH.md).

---

## 0. Vấn đề cốt lõi, được phát biểu lại một cách chính xác

Bản tóm lược nhiệm vụ yêu cầu một tầng tri thức bền vững giúp agent có thể lập luận về một hệ thống hiện có, và hỏi cách làm thế nào để ngăn chặn nó không bị lệch lạc (drift). Đó là hai bài toán hoàn toàn khác nhau và việc đánh đồng chúng chính là lý do khiến các công cụ hiện hữu thất bại:

- **Bài toán A — tính hữu ích (usefulness).** Cung cấp cho agent những tri thức mà nó không thể trích xuất lại từ mã nguồn, dưới một định dạng gần như không tốn chi phí nạp vào ngữ cảnh.
- **Bài toán B — tính đáng tin cậy (trustworthiness).** Giúp chúng ta có thể biết được, một cách cơ học, những phần tri thức nào vẫn còn được xác minh tính đến commit hiện tại, và nghiêm cấm việc âm thầm đối soát theo bất kỳ chiều hướng nào.

Một giải pháp chỉ cho riêng bài toán A chính là 7 bản đồ markdown của GSD: hữu ích, nhưng đang mục rữa dần. Một giải pháp chỉ cho riêng bài toán B là một trình linter quét qua các tài liệu mà không ai thèm đọc. Thiết kế dưới đây giải quyết cả hai bài toán chỉ bằng một cơ chế duy nhất — **khẳng định có neo và được gắn nhãn nguồn chân lý (anchored, truth-source-labelled claim)** — bởi vì một claim vừa là đơn vị của tính hữu ích, vừa là đơn vị của sự kiểm chứng.

### Ba nguyên tắc rút ra từ các bằng chứng thực nghiệm

1. **Lưu trữ các phán đoán, phái sinh các dữ kiện.** Nếu một kỹ sư có năng lực có thể trích xuất lại thông tin đó từ mã nguồn chuẩn mực, thì đó là một dữ kiện (fact) và bắt buộc phải được phái sinh theo nhu cầu, tuyệt đối không lưu trữ cứng. (Tiêu chí kết nạp của BMAD; mục §5.2 trong RESEARCH.md.)
2. **Lỗi thời là một phép so sánh; tính đúng đắn là một phán đoán.** Phép so sánh là việc của kernel. Phán đoán là việc của con người, với LLM đóng vai trò đề xuất. LLM bị sụt giảm từ 21–43 điểm phần trăm độ chính xác phát hiện trong đúng trường hợp chỉ có code thay đổi còn tài liệu giữ nguyên (arXiv:2604.03447), do đó chúng không thể là bộ phát hiện lỗi thời.
3. **Mỗi dòng ngữ cảnh đều phải trả giá trong mọi phiên làm việc.** Tập hợp nạp-liên-tục có một ngân sách cứng không bao giờ được tự ý nâng lên. Mọi thứ khác đều phải nằm sau một điều kiện kích hoạt có thể quan sát được.

---

## 1. Đơn vị tri thức: Claim (Khẳng định)

**Quyết định: metadata có cấu trúc + văn xuôi Markdown, từng claim riêng lẻ, lưu trong git. Không dùng đồ thị, không dùng database, không chỉ dùng YAML thuần, không dùng dữ liệu phái sinh từ AST.**

Tại sao từ chối các phương án thay thế:

| Phương án thay thế | Lý do bị từ chối |
|---|---|
| Văn xuôi Markdown thuần | Không thể định địa chỉ riêng biệt, không thể diff ở cấp độ từng dữ kiện, không thể kiểm tra tự động. Đây là thất bại chung của toàn bộ tài liệu tham chiếu. |
| YAML/JSON thuần | Đánh mất phần văn xuôi giúp tri thức trở nên *dễ sử dụng* đối với con người hoặc agent; không ai đọc hoặc duy trì nó. |
| Đồ thị tri thức (Knowledge graph) | GSD đã xây dựng một cái (`graphify`) và nó trở thành cách biểu diễn thứ tư mang theo câu chuyện lỗi thời riêng của nó. Những mối liên kết mà bạn không thể kiểm chứng còn tồi tệ hơn việc không có liên kết nào. Bị từ chối đối với MVP; xem Q7 trong [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md). |
| Cơ sở dữ liệu (SQLite) | Không thể diff, không thể review trong một PR, không thể merge, vô hình trong `git log`. Hủy hoại đặc tính duy nhất giúp hệ thống này hoạt động: thay đổi tri thức cũng được review y như thay đổi code. |
| Metadata phái sinh từ AST làm kho lưu | Đó là tầng *phái sinh (derived)*, không phải tầng tri thức. Nó chỉ có thể nhắc lại những gì code đã thể hiện. |
| Chỉ mục Embeddings / RAG | Trả lời câu hỏi "cái gì tương tự", không trả lời "điều gì bắt buộc phải đúng". Bổ sung thêm một bước build, thêm một chỉ mục dễ mục rữa, và hoàn toàn không có tính kiểm chứng. |

### 1.1 Hình thái của một Claim

Một claim là một tiêu đề Markdown mang một ID ổn định, theo sau ngay lập tức bởi một khối rào `claim`, rồi đến văn bản văn xuôi. Khối rào này chính là lý do giúp nó có thể được phân tích cú pháp chỉ với ~20 dòng code mà không cần phân tích YAML toàn bộ tài liệu.

```markdown
### INV-7 — A refund never exceeds the captured amount

```claim
kind: invariant
status: enforced
truth-source: tests
anchors:
  - src/payments/refund.ts#computeRefundable@a1b2c3d
  - src/payments/refund.ts#Refund@a1b2c3d
evidence:
  - test: tests/payments/refund.spec.ts::refund cannot exceed capture
governs: [CMP-payments, API-post-refunds]
since: ADR-0014
reviewed: 2026-09-10
```

Khoản hoàn tiền một phần có tính tích lũy: tổng của tất cả các khoản hoàn tiền đã quyết toán đối với một đơn hàng mới là giá trị bị giới hạn, không phải từng khoản hoàn riêng lẻ. Một yêu cầu hoàn tiền vượt quá số dư còn lại sẽ bị từ chối tại ranh giới domain, chứ không bị kẹp gọt (clamped) — việc âm thầm kẹp gọt sẽ khiến khách hàng bị hoàn thiếu tiền, điều này còn tồi tệ hơn là gặp lỗi.
```

Phần văn xuôi là phần mà agent thực sự dùng để lập luận. Khối metadata là phần mà kernel dùng để xử lý cơ học. Phần văn xuôi bắt buộc phải nói lên điều mà mã nguồn không thể tự nói — trong ví dụ này là lý do *tại sao* từ chối lại tốt hơn việc kẹp gọt số tiền — và điều đó được kiểm tra thông qua review của con người, không phải bằng script.

### 1.2 Danh mục các trường dữ liệu

| Trường | Bắt buộc | Giá trị | Ý nghĩa |
|---|---|---|---|
| `kind` | có | xem §2 | Xác định kiểm định nào sẽ được áp dụng |
| `status` | có | `enforced` \| `asserted` \| `proposed` \| `retired` | `enforced` = có một công cụ sẽ báo lỗi khi nó bị vi phạm. `asserted` = tin là đúng, chỉ được neo. `proposed` = chưa được phê chuẩn (chỉ dùng cho ứng viên). `retired` = giữ lại vì lịch sử, loại khỏi các phép kiểm tra |
| `truth-source` | có | `code` \| `tests` \| `config` \| `spec` \| `decision` \| `derived` | Artifact nào nắm giữ thẩm quyền chuẩn tắc cho claim này (§3) |
| `anchors` | có¹ | danh sách `path[#Symbol][@sha]` | Đoạn mã nào trong codebase mà claim này mô tả. Điều khiển việc phát hiện lỗi thời (§5) |
| `evidence` | nếu `status: enforced` | danh sách các mục `test:` / `rule:` / `contract:` / `check:` | Thứ gì sẽ thất bại về mặt cơ học khi claim bị vi phạm (§4) |
| `governs` | không | danh sách các ID claim | Các claim bị ràng buộc bởi claim này. Có hướng, không chu trình |
| `since` | không² | `ADR-nnnn` | Quyết định đã tạo ra hoặc thay đổi claim này lần gần nhất |
| `supersedes` | không | ID claim | Thay thế cho một claim đã bị hủy bỏ (retired) |
| `reviewed` | có | `YYYY-MM-DD` | Ngày mà con người xác nhận lại phần văn xuôi lần cuối. Không phải tín hiệu lỗi thời; là tín hiệu nợ review |
| `confidence` | chỉ ứng viên | `high` \| `medium` \| `low` | Chỉ xuất hiện ở đầu ra bootstrap; bị cấm trong các claim đã phê chuẩn |

¹ Trường `anchors` có thể là mảng rỗng `[]` **khi và chỉ khi** có `kind: constraint` (các ràng buộc bắt nguồn từ bên ngoài repository) và `kind: concept` (từ vựng không thuộc về một vị trí duy nhất nào). Để trống neo ở bất kỳ loại nào khác sẽ là một lỗi kiểm định, vì một claim không có neo sẽ không bao giờ có thể kiểm tra được và sẽ âm thầm mục rữa.

² Trường `since` là **bắt buộc** đối với `kind: architecture` và đối với bất kỳ claim nào có `status` chuyển đổi từ `asserted` sang `enforced` hoặc ngược lại. Lý do: đó là những thay đổi đòi hỏi phải có một lý do được ghi nhận rõ ràng.

### 1.3 Tại sao ID lại quan trọng hơn vẻ bề ngoài của nó

Các ID là toàn bộ nền tảng cho khả năng truy vết (§8). Các hệ quả, tất cả đều được kế thừa từ những gì phát huy hiệu quả trong tài liệu tham chiếu:

- **Ổn định, không bao giờ đánh số lại hay tái sử dụng** (BMAD `AD-n`). Một ID claim là một cái tên vĩnh viễn.
- **Trích dẫn nguyên văn, không bao giờ diễn giải lại** (GSD `CONTEXT.md`). Một đề xuất thay đổi sẽ viết `INV-7`, không viết "bất biến hoàn tiền". Điều này giúp lệnh `grep -r INV-7` trở thành câu trả lời hoàn chỉnh cho câu hỏi "mục này đang giữ vai trò trụ cột ở đâu?".
- **Một claim cho mỗi ID, một ID cho mỗi tiêu đề neo dòng**, để `git blame` trên dòng tiêu đề cho bạn biết ai đã đưa claim này vào và `git log -S INV-7` cho bạn biết mọi artifact từng tham chiếu đến nó.

---

## 2. Các loại Claim, các tệp lưu trữ, và những gì bắt buộc

### 2.1 Cấu trúc kho lưu trữ (The store)

```
docs/system/
  OVERVIEW.md              # văn xuôi, <= 1 trang, luôn luôn được nạp. Không chứa claim.
  architecture.md          # ARC-*  bắt buộc
  components.md            # CMP-*  bắt buộc
  domain.md                # CON-*, INV-*  bắt buộc
  pitfalls.md              # PIT-*  bắt buộc (có thể rỗng khi mới khởi tạo)
  interfaces.md            # API-*  tùy chọn
  data.md                  # DAT-*  tùy chọn
  workflows.md             # FLW-*  tùy chọn
  constraints.md           # CST-*  tùy chọn
  strategy.md              # STR-*  tùy chọn
  decisions/
    ADR-0001-<slug>.md     # thư mục bắt buộc; có thể rỗng khi mới khởi tạo
  derived/                 # do máy sở hữu. Tuyệt đối không sửa tay. Có thể tái tạo lại.
    inventory.json
    api-surface.json
    deps.json
    tests.json
    trace.json
    drift.json
  candidates/              # chưa phê chuẩn. Agent CÓ THỂ đọc; KHÔNG ĐƯỢC trích dẫn làm chân lý.
    <topic>.md
  DRIFT.md                 # sổ cái độ lệch đang mở (§6)
  DEBT.md                  # sổ đăng ký khiếm khuyết kỹ thuật (§9)
```

**Lý do phân tách theo loại thay vì theo hệ thống con.** Các loại khác nhau có các nguồn chân lý khác nhau và nhịp độ cập nhật khác nhau. Nếu `architecture.md` cũng chứa danh sách công nghệ (stack), câu hỏi "tệp này có bị lỗi thời không?" sẽ không có câu trả lời rõ ràng. Phân tách theo loại giúp cho việc xác định tính lỗi thời theo từng tệp trở nên có ý nghĩa, điều này làm cho các cổng kiểm soát vận hành hiệu quả. (Đây là sự chỉnh sửa đối với tệp spine duy nhất của BMAD được ghi nhận trong COMPETITIVE_ANALYSIS.md §2.3.)

**Lý do dùng một tệp phẳng cho mỗi loại thay vì một tệp cho mỗi claim.** Một tệp cho mỗi claim sẽ tạo ra 200 tệp tin vụn vặt và một `git log` không thể đọc nổi. Một tệp cho mỗi loại có thể đọc từ trên xuống dưới như một tài liệu hoàn chỉnh, trong khi các claim vẫn có thể được định địa chỉ độc lập theo ID.

### 2.2 Chi tiết từng loại Claim

| Loại | Tiền tố | Trả lời điều gì | `truth-source` mặc định | Có thể cơ giới hóa? |
|---|---|---|---|---|
| `architecture` | `ARC-` | Cấu trúc nào bắt buộc phải tôn trọng? Hướng phụ thuộc, phân tầng, ghép nối cho phép, cấm chu trình, "chỉ X mới được gọi Y" | `decision` | **Thường là có** — quy tắc dependency-cruiser / ArchUnit / Tach / Deptrac |
| `component` | `CMP-` | Các phần có tên là gì, mỗi phần chịu trách nhiệm gì, ranh giới ở đâu? | `decision` | Một phần — path glob có thể kiểm tra, trách nhiệm thì không |
| `concept` | `CON-` | Từ ngữ domain này có ý nghĩa gì ở đây, và nó *không phải* là gì? | `decision` | Không |
| `invariant` | `INV-` | Đặc tính nào bắt buộc phải luôn luôn duy trì? | `tests` | **Có** — một bài test có tên cụ thể |
| `interface` | `API-` | Hợp đồng bên ngoài là gì và chính sách tương thích ra sao? | `spec` hoặc `code` | **Có** — tệp hợp đồng + cổng kiểm soát mức độ nghiêm trọng của `oasdiff` |
| `datum` | `DAT-` | Mô hình dữ liệu có ý nghĩa gì, quy tắc định danh/sở hữu là gì, chính sách migration nào được áp dụng? | `code` (schema) hoặc `decision` | Một phần — diff snapshot schema, sự hiện diện của migration |
| `workflow` | `FLW-` | Trình tự end-to-end là gì, và điều gì không được đảo trật tự hoặc bỏ qua? | `code` | Hiếm khi — thỉnh thoảng là một integration test |
| `constraint` | `CST-` | Những gì bị áp đặt từ bên ngoài repository? Tuân thủ pháp lý, SLA, hợp đồng, giấy phép, nền tảng | `decision` | Đôi khi — một bài kiểm tra hoặc quét chính sách |
| `strategy` | `STR-` | Những gì *bắt buộc* phải test thế nào / deploy thế nào / bảo mật thế nào? (chính sách, không phải hiện trạng) | `decision` | Đôi khi — ngưỡng bao phủ, CI job bắt buộc |
| `pitfall` | `PIT-` | Những gì mà agent và con người liên tục làm sai ở đây? | bằng chứng quan sát được (`decision`) | Đôi khi — kết quả tốt nhất là biến nó thành rule linter và hủy bỏ claim |

**Bắt buộc tại thời điểm ban đầu:** `architecture.md`, `components.md`, `domain.md`, `pitfalls.md`, `decisions/`. Các tệp còn lại sẽ được tạo khi dự án thực sự có bề mặt đó — một thư viện nội bộ sẽ không có `interfaces.md`, và việc tạo một tệp rỗng chỉ gây thêm tiếng ồn.

**Giá trị cao nhất trên mỗi dòng, theo nhận định của tôi:** `PIT-` và `CON-`. Một cạm bẫy là tri thức *đã được trả giá* bằng một thất bại trong quá khứ và không thể tự phái sinh từ bất kỳ thứ gì. Một khái niệm ngăn chặn cả một lớp code sai lầm bằng cách cố định từ vựng. Cả hai đều rẻ, cả hai đều vô hình đối với bất kỳ phân tích tĩnh nào, và cả hai là những thứ mà tài liệu do AI tự động sinh ra không bao giờ có được.

**Giá trị thấp nhất trên mỗi dòng:** bất kỳ thứ gì chỉ nhắc lại cấu trúc. Tệp `components.md` là tệp dễ bị thoái hóa thành một bản liệt kê thư mục nhất, và quá trình kiểm định nó cần phải kiên quyết loại trừ điều đó (§7.3).

### 2.3 Tầng phái sinh (The derived tier)

Thư mục `docs/system/derived/*.json` được sinh ra bởi lệnh `forge sync`, do máy sở hữu, và mang theo thông tin xuất xứ:

```json
{
  "$schema": "forge/derived/v1",
  "generated_from_commit": "a1b2c3d4e5f6",
  "generator": "forge sync derived",
  "tool": "dependency-cruiser@16.3.3",
  "data": { }
}
```

> **Được đính chính bởi quá trình triển khai thực tế, 2026-09-10.** Phần vỏ bọc này ban đầu có trường dấu thời gian `generated_at`. Nó không thể có trường này: một dấu thời gian khiến mỗi lần tạo lại đều sinh ra các byte khác nhau, do đó hai nguyên tắc "tái tạo là no-op" và "tệp phái sinh bị sửa tay là một lỗi" — cả hai đều được nêu bên dưới — không thể cùng lúc đúng. Commit ID mới là dữ liệu xuất xứ thực sự có ý nghĩa, và nó là thứ mà tín hiệu lỗi thời mang ra so sánh.

Các quy tắc:

- **Tuyệt đối không sửa tay.** Một sửa đổi bằng tay sẽ bị phát hiện vì việc tạo lại sinh ra một tệp khác; `forge check` thất bại khi tệp phái sinh bị bẩn (dirty).
- **Không bao giờ trích dẫn làm thẩm quyền trong văn xuôi của claim.** Các claim trích dẫn các neo và bằng chứng; dữ liệu phái sinh dành cho *agent đọc* và để tính toán phạm vi ảnh hưởng.
- **Được commit vào git, không đưa vào gitignore.** Commit chúng giúp cho diff của chúng hiển thị rõ ràng trong các đợt review, đó là cách bạn nhận ra bề mặt API đã bị thay đổi. Đây là sự đánh đổi có chủ ý giữa tiếng ồn repository để lấy khả năng review.
- **Tính lỗi thời là `generated_from_commit != HEAD`**, được báo cáo dưới dạng `commits_behind` (cơ chế của GSD), tuyệt đối không dùng ngưỡng thời gian thực (tệp `intel` của GSD dùng mốc 24 giờ; điều đó là sai lầm và các công trình sau này của chính họ đã thay thế nó).

Nội dung, theo thứ tự giá trị:

| Tệp | Nội dung | Tạo ra bởi |
|---|---|---|
| `inventory.json` | các tệp được theo dõi theo ngôn ngữ, LOC, điểm nhập, tệp test, tệp cấu hình, stack + phiên bản ghim đọc từ lockfile | git + globs + đọc lockfile |
| `deps.json` | các cạnh import module→module, chu trình, fan-in/fan-out theo từng component | công cụ hệ sinh thái (dependency-cruiser / tach / go list / cargo tree …) |
| `api-surface.json` | các symbol được export kèm chữ ký hàm theo từng public module; route HTTP nếu phát hiện được | tree-sitter / công cụ hệ sinh thái |
| `tests.json` | tệp test → danh sách tên test, cộng với các ID requirement/claim mà mỗi test khai báo (§8.2) | test runner `--list` hoặc grep |
| `trace.json` | chỉ mục truy vết (§8) | tính toán từ các tệp khác + phân tích claim/change |
| `drift.json` | kết quả kiểm tra độ lỗi thời neo và tuân thủ quy tắc hiện tại | `forge drift` |

### 2.4 Tầng ứng viên (The candidates tier)

Quá trình bootstrap và điều tra sẽ ghi vào đây (`docs/system/candidates/`). Sự phân biệt này được thực thi bằng máy, không phải là phong cách viết:

- Một claim ứng viên có `status: proposed` và một trường `confidence`.
- Agent **có thể đọc** các ứng viên và **tuyệt đối không được trích dẫn** chúng như những sự thật đã được xác lập. Khi đầu ra của một phase dựa vào một ứng viên, nó phải nói rõ điều đó và coi đó là một giả định.
- `forge check` thất bại nếu trường `governs` hoặc `since` của bất kỳ claim đã phê chuẩn nào trỏ vào thư mục candidates.
- Phê chuẩn là một hành động của con người (`forge ratify <ID>`), thao tác này sẽ chuyển claim vào tệp đúng loại của nó, gỡ bỏ `confidence`, thiết lập `reviewed`, và đóng dấu các neo với SHA hiện tại.

Tầng này là câu trả lời cho phần cốt lõi trung thực của bài toán bootstrap: một LLM đọc một codebase xa lạ sẽ đưa ra các claim nghe rất hợp lý, và tri thức nghe-có-vẻ-đúng-nhưng-thực-ra-sai còn tệ hơn là không có tri thức nào. Thư mục candidates biến trạng thái "nghe có vẻ hợp lý" thành một trạng thái hạng nhất thay vì vội vã hợp thức hóa nó thành chân lý.

---

## 3. Các nguồn chân lý và thứ tự ưu tiên

### 3.1 Bảng thẩm quyền theo từng dữ kiện

Không tồn tại một nguồn chân lý toàn cục duy nhất. Mỗi *loại câu hỏi* đều có một thẩm quyền chuẩn tắc riêng, và bảng này chính là bản hiến chương của harness cho việc xử lý các mâu thuẫn.

| Câu hỏi | Thẩm quyền | Ai có quyền thay đổi |
|---|---|---|
| Hệ thống đang làm gì ngay lúc này? | mã nguồn, cộng với các bài test hiện đang pass | bất kỳ thay đổi code nào |
| Hệ thống bắt buộc phải làm gì (hành vi quan sát được từ bên ngoài)? | các bản spec năng lực vĩnh viễn | một thay đổi có delta spec |
| Đặc tính nào bắt buộc phải luôn luôn duy trì? | claim `INV-`, được giải tỏa bởi một bài test cụ thể | một thay đổi có `impact.md` nêu tên claim đó |
| Cấu trúc nào bắt buộc phải được tôn trọng? | claim `ARC-`, được thực thi bởi một tệp quy tắc | một thay đổi có kèm một bản ADR |
| Hợp đồng bên ngoài là gì? | artifact hợp đồng (OpenAPI/proto/schema), được sinh từ code hoặc dùng để sinh ra code | một thay đổi có contract diff nằm dưới ngưỡng nghiêm trọng, hoặc một ADR nếu vượt ngưỡng |
| Tại sao nó lại được thiết kế như thế này? | bản ADR | một ADR mới (không bao giờ sửa ADR cũ; thay thế bằng ADR mới) |
| Hiện trạng hình thái, stack, bề mặt của repo là gì? | thư mục `derived/` | chỉ lệnh `forge sync` |
| Chúng ta liên tục mắc phải lỗi gì? | các claim `PIT-` | bất kỳ ai, dựa trên bằng chứng quan sát được |

### 3.2 Thế nào thực sự là một "mâu thuẫn" (contradiction)

Một mâu thuẫn chỉ có ý nghĩa **giữa một claim và thẩm quyền được khai báo của chính nó**. Đây là điểm mà ví dụ ở mục §3 trong bản tóm lược nhiệm vụ cần được làm sắc nét:

> `architecture.md` nói `Payment Service → PostgreSQL`, mã nguồn hiện tại lại gọi `Payment Service → Redis`.

Đó không phải là hai thực thể ngang hàng đang bất đồng ý kiến. Nó giải quyết thành chính xác một trong bốn tình huống sau, và nhiệm vụ của harness là *từ chối đoán mò*:

| Phán quyết | Ý nghĩa | Cách giải quyết bắt buộc |
|---|---|---|
| **V1 — code sai** | Claim vẫn là chính sách đang hiệu lực; phần triển khai code đã vi phạm nó | Sửa lại code. Claim giữ nguyên. Nếu claim đang là `asserted`, hãy nâng cấp nó lên `enforced` bằng cách thêm một rule kiểm tra để lỗi này không lặp lại |
| **V2 — claim chưa từng đúng** | Claim đã bị sai ngay từ lúc viết (nhiễu từ bootstrap, hoặc nhầm lẫn) | Đính chính lại claim. **Không cần ADR** — chưa từng có quyết định nào được đưa ra, chỉ là ghi nhận sai. Ghi nhận bằng chứng vào sổ cái độ lệch |
| **V3 — quyết định đã thay đổi** | Ai đó đã chủ ý chuyển sang dùng Redis | **Bắt buộc phải có một ADR** thay thế quyết định trước đó, cộng với việc cập nhật claim, cộng với cập nhật tệp quy tắc. Bản ADR là artifact hợp thức hóa điều này |
| **V4 — claim chưa đủ cụ thể** | Cả PostgreSQL và Redis đều tương thích với ý định thực sự; claim trước đó quá cụ thể hóa | Tinh chỉnh lại claim để nêu ràng buộc thực chất (ví dụ: "sổ cái thanh toán phải đảm bảo tính bền vững và tính giao dịch") và bổ sung quy tắc kiểm tra thực tế |

**Harness không bao giờ tự ý chọn phán quyết.** Nó phát hiện, phân loại trong chừng mực bằng chứng cho phép, đề xuất một phán quyết kèm lập luận, và chặn tiến trình cho đến khi con người ghi nhận một phán quyết. Đây là hệ quả trực tiếp từ nghiên cứu arXiv:2604.03447: khả năng phán đoán của mô hình ở đây yếu nhất một cách có hệ thống và độ tự tin của nó không mang giá trị phân biệt.

**Việc tự động đối soát (Auto-reconciliation) bị nghiêm cấm theo thiết kế**, không phải bằng lời khuyên: `forge` không có lệnh nào tự động viết lại một claim từ mã nguồn. Hành vi `drift_action: auto-remap` của GSD chính xác là thứ mà chúng ta loại trừ.

### 3.3 Một sự bất đối xứng duy nhất mà chúng ta cho phép

Thư mục `derived/` có thể được tạo lại từ code một cách tự do và không cần thủ tục phê duyệt, bởi vì nó không đưa ra bất kỳ khẳng định mang tính quy chuẩn (normative) nào. Điều này là có chủ đích: nó mang lại cho thôi thúc "hãy làm cho tài liệu khớp với code" một lối thoát hợp pháp mà không thể hủy hoại các quyết định kiến trúc đã đưa ra.

---

## 4. Cơ giới hóa khả năng kiểm tra của các Claim

Phần này là điểm khác biệt cốt lõi giữa thiết kế này và mọi thứ trong tài liệu tham chiếu.

### 4.1 `status: enforced` bắt buộc phải có bằng chứng có tên

Một claim chỉ có thể mang `status: enforced` nếu trường `evidence` của nó nêu tên ít nhất một artifact sẽ thất bại khi claim bị vi phạm, và kernel phải xác minh được rằng artifact đó tồn tại và đang pass. Các dạng của mục bằng chứng:

```yaml
evidence:
  - test: tests/payments/refund.spec.ts::refund cannot exceed capture
  - rule: .forge/rules/deps.cjs#no-domain-to-web
  - contract: contracts/payments.openapi.yaml
  - check: scripts/checks/no-raw-db-client.sh
```

| Dạng | Được kernel xác minh bằng cách | Loại claim điển hình |
|---|---|---|
| `test:` | bài test đó tồn tại trong `derived/tests.json` **và** đã pass trong lần chạy verify gần nhất | `INV-`, `FLW-`, `DAT-` |
| `rule:` | id quy tắc đó tồn tại trong tệp quy tắc được nêu tên **và** công cụ kiểm tra trả về exit 0 | `ARC-`, `CMP-` |
| `contract:` | tệp hợp đồng đó tồn tại **và** `oasdiff` (hoặc tương đương) đối chiếu với hợp đồng tạo lại nằm trong ngưỡng nghiêm trọng cho phép | `API-` |
| `check:` | script đó tồn tại **và** trả về exit 0 | `CST-`, `STR-`, `PIT-` |

### 4.2 Biên dịch các claim kiến trúc thành các quy tắc thực tế

Đối với các claim `ARC-`, phần văn xuôi `Rule` được ánh xạ tới chính công cụ kiểm tra tuân thủ của hệ sinh thái. Harness không tự triển khai kiểm tra tuân thủ; nó duy trì tệp cấu hình và liên kết nó với claim.

```markdown
### ARC-3 — The domain layer must not depend on transport or persistence

```claim
kind: architecture
status: enforced
truth-source: decision
anchors:
  - src/domain/@a1b2c3d
evidence:
  - rule: .forge/rules/deps.cjs#domain-no-outbound
governs: [CMP-domain, CMP-web, CMP-repos]
since: ADR-0002
reviewed: 2026-09-10
```

Ngăn chặn: một quy tắc domain trở nên không thể kiểm thử được vì việc khởi tạo nó đòi hỏi một cơ sở dữ liệu hoặc một HTTP request. Chỉ thực thi cho `src/domain/**`; `src/app/**` là tầng kết hợp và được miễn trừ.
```

và trong `.forge/rules/deps.cjs`:

```js
{
  name: 'domain-no-outbound',           // <- id mà ARC-3 liên kết tới
  comment: 'forge:ARC-3',               // <- tham chiếu ngược, có thể grep được
  severity: 'error',
  from: { path: '^src/domain/' },
  to:   { path: '^src/(web|repos|infra)/' }
}
```

Mối liên kết hai chiều (`evidence: rule:` xuôi, `comment: forge:ARC-3` ngược) được kiểm tra bởi `forge check`: một rule được gắn thẻ `forge:ARC-3` mà `ARC-3` không tồn tại là một lỗi, và một claim `ARC-` được đánh dấu `enforced` mà id rule của nó bị thiếu là một lỗi. **Đây chính là cách giúp "độ lệch kiến trúc" không còn là bài toán AI đối với những claim quan trọng nhất.**

### 4.3 Tỷ lệ `enforced` / `asserted` là một chỉ số được báo cáo rõ ràng

Lệnh `forge status` in ra, theo từng loại, có bao nhiêu claim là `enforced` so với `asserted`. Các claim chưa được cơ giới hóa vẫn hoàn toàn hợp lệ — hầu hết các claim `CON-` và nhiều claim `CMP-` không thể cơ giới hóa — nhưng tỷ lệ này bắt buộc phải *nhìn thấy được* thay vì ngầm định. Một dự án mà các claim kiến trúc có tỷ lệ 100% `asserted` đồng nghĩa với việc hoàn toàn không có sự tuân thủ kiến trúc tự động nào, và dự án cần phải biết rõ điều đó.

**Các mục tiêu baseline khuyến nghị** (dự án có thể tự cấu hình, kernel không ép buộc):
`INV-` ≥ 80% enforced, `ARC-` ≥ 60% enforced, `API-` 100% enforced ở nơi có hợp đồng giao diện. Mọi loại khác: không đặt mục tiêu.

---

## 5. Phát hiện tri thức bị lỗi thời (Stale Knowledge)

### 5.1 Nguyên thủy Anchor (Neo)

Kế thừa từ linter `drift` của Fiberplane (RESEARCH.md §9.1). Một anchor có định dạng:

```
path[#Symbol][@sha]
src/payments/refund.ts#computeRefundable@a1b2c3d
src/domain/@a1b2c3d                              # neo thư mục: dùng git tree hash
```

Lệnh `forge drift` thực hiện cho mỗi anchor:

1. Phân giải baseline: `@sha` của neo; nếu không có, lấy commit chạm vào tệp của claim lần gần nhất.
2. Trích xuất đơn vị được neo tại baseline (`git show <sha>:<path>`, rồi thu hẹp vào `#Symbol`).
3. Trích xuất đơn vị tương tự tại `HEAD`.
4. So sánh **dấu vân tay AST đã chuẩn hóa (normalised AST fingerprints)**: phân tích cú pháp bằng tree-sitter, băm chuỗi các cặp `(node_kind, token_text)` sau khi đã loại bỏ khoảng trắng, comment và vị trí dòng. Các ngôn ngữ không có sẵn ngữ pháp tree-sitter sẽ hạ cấp về hàm băm nội dung đã chuẩn hóa khoảng trắng, và claim được báo cáo là `coarse: true` để người dùng thấy rõ tín hiệu này yếu hơn.
5. Phân loại:

| Trạng thái | Ý nghĩa |
|---|---|
| `fresh` | fingerprint hoàn toàn không đổi kể từ baseline |
| `shifted` | **phần thân (body)** của symbol thay đổi, signature giữ nguyên → tín hiệu yếu hơn |
| `stale` | signature thay đổi, hoặc một neo không phải symbol bị thay đổi → claim ở trạng thái **chưa được xác minh**, chưa hẳn đã sai |
| `missing` | đường dẫn hoặc symbol của neo không còn tồn tại nữa → **chặn (blocking)**; một claim nói về đoạn code đã biến mất thì hoặc là bị hủy bỏ (retired) hoặc phải được neo lại (re-anchored) |

Cộng thêm hai cờ (flags) đi kèm với trạng thái thay vì thay thế nó: `coarse` (không có ngữ pháp cho tệp này, việc so sánh dựa trên dòng và yếu hơn) và `symbol_unresolved` (bảng khai báo không thể định vị được symbol, do đó toàn bộ tệp được đem ra so sánh).

> **Được đính chính bởi phép đo lường thực tế, 2026-09-10.** Bảng này ban đầu liệt kê 4 trạng thái với `coarse` là trạng thái thứ tư. Quá trình triển khai M1 đã thay đổi nó hai lần. `coarse` trở thành một cờ vì một phép so sánh coarse vẫn mang lại một phán quyết, và việc gộp nó vào trạng thái sẽ vứt bỏ phán quyết đó. `shifted` được bổ sung vì phép đo lường cho thấy các thay đổi chỉ ở phần thân chiếm tới 79% tổng số phán quyết không-tươi-mới (176 trên 222 trường hợp qua 600 commit) — việc mặc định hiển thị chúng sẽ làm tăng gấp bốn lần kích thước sổ cái. Xem [docs/measurements/M1-anchor-stability.md](docs/measurements/M1-anchor-stability.md).

**Những gì cơ chế này mang lại một cách chính xác:** đối với mỗi claim, một câu trả lời mang tính xác định, không phụ thuộc vào định dạng cho câu hỏi: "đoạn code mà claim này mô tả có bị thay đổi kể từ lần cuối cùng con người xác nhận claim hay không?" Đó không phải là câu hỏi "claim này có đúng không", và việc giả vờ ngược lại là nơi mọi công cụ khác đi chệch hướng. Tuy nhiên, nó là chính xác tập hợp các claim mà một reviewer cần phải xem xét — và nó được tính toán bằng git và tree-sitter, không tốn một lệnh gọi mô hình nào, chỉ mất vài giây.

**Điểm yếu đã biết (cũng là của Fiberplane, và là rủi ro triển khai lớn nhất của chúng ta).** Một thao tác đổi tên hoặc di chuyển tệp sẽ đánh dấu mọi neo trên symbol đó là stale. Các biện pháp giảm thiểu, theo thứ tự: dùng `git log --follow` / tính năng phát hiện đổi tên khi phân giải baseline; ưu tiên neo `#Symbol` hơn là neo theo dòng (đã nằm trong thiết kế); cho phép `forge reanchor <ID>` đóng dấu lại một neo *khi và chỉ khi* fingerprint không đổi sau khi áp dụng ánh xạ đổi tên của git — nghĩa là việc re-anchor là miễn phí khi không có thay đổi ngữ nghĩa nào và không thể thực hiện khi có thay đổi. Xem Q3 trong [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).

### 5.2 Ba tín hiệu lỗi thời bổ sung, đều mang tính xác định

| Tín hiệu | Cách tính toán | Mức độ nghiêm trọng | Kế thừa từ |
|---|---|---|---|
| **Lỗi thời tầng phái sinh** | `generated_from_commit != HEAD`; báo cáo `commits_behind` | cảnh báo; chặn tại `verify` | `built_at_commit` của GSD |
| **Lỗi thời tiền đề (Premise)** | thời gian commit cuối của artifact thay đổi cũ hơn commit mới nhất chạm vào bất kỳ claim nào nó trích dẫn | cảnh báo tại `plan`, chặn tại `implement` | cổng context-drift của GSD |
| **Nợ review (Review debt)** | `reviewed` cũ hơn N commit chạm vào neo của claim (mặc định N=50), hoặc cũ hơn 12 tháng | chỉ cảnh báo, không bao giờ chặn | dòng xuất xứ của BMAD |
| **Xóa đối tượng tham chiếu** | `git log --diff-filter=DR --name-only <sha>..HEAD` giao cắt với các đường dẫn neo | chặn (tương tự như `missing`) | quy trình refresh của BMAD |

Nợ review được chủ ý thiết kế là không chặn. Một cổng nợ review mang tính chặn sẽ tập cho bạn thói quen click bừa cho qua, điều này phá hủy giá trị của mọi cổng kiểm soát khác.

### 5.3 Độ lệch cấu trúc: Tri thức đáng lẽ phải có nhưng lại vắng bóng

Các tín hiệu ở trên tìm ra các claim *bị* lỗi thời. Khoảng trống ngược lại — hệ thống mọc thêm thứ gì đó mà không có claim nào mô tả — cần đến bộ phát hiện cấu trúc của GSD, được tổng quát hóa và làm cho chính xác nhờ tầng phái sinh của chúng ta:

Đối với mỗi tệp mã nguồn mới được thêm vào trong git diff, tính toán component của nó bằng cách so khớp với các path glob của các claim `CMP-`. Nếu nó không khớp với claim nào, nó là tệp **chưa được ánh xạ (unmapped)**. Báo cáo các tệp chưa được ánh xạ gom nhóm theo thư mục, cộng với các module route mới, các migration mới, và các public export mới vắng mặt trong `api-surface.json`. Dựa trên ngưỡng (mặc định là 3 tệp), không chặn tiến trình, và — không giống như GSD — nó không bao giờ tự động map lại: nó xuất ra một đề xuất.

Điều này vượt trội hoàn toàn so với thao tác `structureMd.includes(prefix)` của GSD vì các claim `CMP-` mang các path glob tường minh thay vì văn xuôi tự do tình cờ nhắc đến tên thư mục.

---

## 6. Sổ cái độ lệch và giao thức phán quyết

Tệp `docs/system/DRIFT.md` là sổ cái mở. Máy tự động ghi thêm vào, con người giải quyết.

```markdown
## D-014 — INV-7 unverified
```drift
claim: INV-7
detected: 2026-09-10
detected_by: forge drift
signal: stale
anchors_changed:
  - src/payments/refund.ts#computeRefundable  (a1b2c3d -> f7e8d9a)
diff_summary: "computeRefundable now consults a Redis cache before the ledger"
proposed_verdict: V3
proposed_reasoning: |
  Thay đổi này đưa vào việc đọc cache trên luồng mà invariant đang ràng buộc.
  Test giải tỏa của invariant vẫn pass, vì vậy đặc tính dường như được bảo toàn,
  nhưng rule của ARC-3 hiện báo cáo một cạnh phụ thuộc mới từ domain sang infra.
status: open
```
```

Việc giải quyết được thực hiện qua `forge drift resolve D-014 --verdict V3 --adr 0021` (hoặc `--verdict V1`, `--verdict V2 --evidence <note>`, `--verdict V4`). Kernel thực thi các hệ quả:

| Phán quyết | Kernel thực thi |
|---|---|
| V1 code sai | Mục sổ cái giữ trạng thái mở cho đến khi fingerprint của neo khớp trở lại, hoặc một thay đổi sửa lại code. Claim giữ nguyên. Nhắc nhở thêm rule nếu đang là `status: asserted` |
| V2 claim chưa từng đúng | Claim được phép sửa **mà không cần** ADR. Bắt buộc phải có ghi chú `--evidence` không rỗng, được ghi lại vào sổ cái. Các neo được đóng dấu lại |
| V3 quyết định thay đổi | **Bắt buộc** phải có ID của một ADR hiện hữu mà trường `supersedes` của nó nêu tên quyết định trước đó. Cho phép sửa claim, cập nhật trường `since:`, đóng dấu lại các neo. Từ chối nếu ADR không tồn tại |
| V4 chưa đủ cụ thể | Cho phép sửa claim; yêu cầu claim mới phải có `status: enforced` kèm bằng chứng mới, hoặc một cờ `--accept-asserted` tường minh được ghi nhận vào sổ cái |

Mỗi lần giải quyết là một commit chạm vào cả sổ cái lẫn claim cùng một lúc, do đó lý do lập luận và việc chỉnh sửa tạo thành một đơn vị có thể review được trọn vẹn.

**Các quyền miễn trừ (Waivers).** Lệnh `forge drift waive D-014 --until <sha|date> --reason "<text>"` tồn tại vì phương án thay thế là một cổng kiểm soát vĩnh viễn báo đỏ mà người ta sẽ tìm cách tắt đi. Một quyền miễn trừ được ghi nhận, có thời hạn hết hạn, và được liệt kê bởi `forge status`. Đây là khuôn mẫu `skip_specs: true` của OpenSpec: làm cho sự bỏ qua trở nên tường minh, có tên, và được commit vào git.

---

## 7. Kiểm định: Những gì Kernel kiểm tra

Tất cả những điều sau đây đều là các script xác định. Không có kiểm tra nào gọi tới mô hình LLM.

### 7.1 Cấu trúc (theo từng tệp, từng claim)

1. ID của claim khớp với `^(ARC|CMP|CON|INV|API|DAT|FLW|CST|STR|PIT)-(\d+|[a-z0-9][a-z0-9-]*)$` — một số hoặc một slug kebab. *Được đính chính bởi quá trình triển khai, 2026-09-10: quy tắc này ban đầu chỉ cho phép số, trong khi mọi ví dụ trong tài liệu này đều dùng slug (`CMP-payments`, `CON-capture`, `API-post-refunds`). Dạng slug thắng thế vì `grep -r CMP-payments` tự thân nó đã rõ nghĩa. Thứ được thực thi là **tính ổn định**, không phải tính chất chỉ gồm số — token là vĩnh viễn, vì vậy một component được đổi tên từ payments thành billing vẫn giữ nguyên `CMP-payments` và chỉ đổi tiêu đề.*
2. ID là duy nhất trên toàn bộ kho lưu trữ; không bao giờ được tái sử dụng (được kiểm tra đối chiếu với `git log -S` cho ID trong các claim đã retire). Các ID dạng số phải tăng dần trong một tệp; dạng slug không có thứ tự, vì vậy kiểm tra tăng dần chỉ áp dụng cho dạng số.
3. Mọi claim đều có khối rào `claim` đúng quy chuẩn, và mọi trường bắt buộc đều hiện diện và nằm trong tập giá trị cho phép.
4. Trường `anchors` không được rỗng trừ khi `kind` ∈ {`constraint`, `concept`}.
5. `status: enforced` ⇒ `evidence` không được rỗng và mọi mục đều phân giải được.
6. `kind: architecture` ⇒ `since` hiện diện và tệp ADR tương ứng phải tồn tại.
7. Các mục tiêu trong `governs` phải tồn tại, không tự tham chiếu, và đồ thị là phi chu trình.
8. Các mục tiêu trong `supersedes` phải tồn tại và có `status: retired`.
9. Tuyệt đối không có placeholder ở bất kỳ đâu: `TBD`, `TODO`, `FIXME`, `XXX`, `{template-token}`, `[NEEDS CLARIFICATION`, `similar to <ID>`. Các khối code fence được làm trắng trước khi quét (kỹ thuật `lint_spine.py` của BMAD) để các ví dụ minh họa không tạo dương tính giả trong khi số dòng vẫn hoàn toàn chính xác.
10. Không có trường `confidence` bên ngoài thư mục `candidates/`; mọi claim trong `candidates/` đều có `status: proposed`.
11. Phần thân văn xuôi không được rỗng và phải có ít nhất ~2 dòng — một claim có tiêu đề mà không có phần giải thích chỉ là một cái nhãn, không phải tri thức.

### 7.2 Xuyên suốt các Artifact

12. Mọi tham chiếu ngược `forge:<ID>` trong một rule/test/comment code đều phải nêu tên một claim đang tồn tại và chưa bị retire.
13. Mọi mục `evidence: test:` đều phải xuất hiện trong `derived/tests.json`.
14. Mọi id `evidence: rule:` đều phải xuất hiện trong tệp quy tắc được nêu tên.
15. Mọi yêu cầu `REQ-*` trong spec vĩnh viễn đều được giải tỏa bởi ≥1 bài test (§8.2).
16. Không có claim đã phê chuẩn nào được phép tham chiếu đến thứ gì nằm trong `candidates/`.
17. Thư mục `derived/` phải sạch sẽ (tái tạo là no-op) và `generated_from_commit == HEAD` tại thời điểm `verify`.
18. Ngân sách nạp-liên-tục: `OVERVIEW.md` + các tệp claim bắt buộc ≤ ngân sách dòng đã cấu hình (mặc định 400). Vượt quá ngân sách là một **lỗi (ERROR)**, và cách khắc phục duy nhất là cắt giảm hoặc di chuyển bớt.

### 7.3 Các kiểm tra chống nhiễu (những kiểm tra thú vị nhất)

Những kiểm tra này tồn tại nhằm mục đích ngăn chặn việc kho lưu trữ thoái hóa thành một bản sao chép lại code do AI tự động viết. Mỗi kiểm tra là một heuristic và mỗi kiểm tra là một **cảnh báo (warning)** kèm lộ trình xác nhận rõ ràng — đặt lỗi cứng ở đây sẽ quá cứng nhắc:

19. **Mùi claim có thể phái sinh (Derivable-claim smell).** Một claim có phần văn xuôi chứa >60% các định danh xuất hiện trong chính các neo của nó, và không chứa động từ khuyết thiếu nào (`must`, `never`, `always`, `may not`), sẽ bị gắn cờ: nó có thể chỉ đang nhắc lại code. Xác nhận bằng cách thêm `# forge:not-derivable <reason>` trên claim.
20. **Mùi liệt kê thư mục (Directory-listing smell).** Một claim `CMP-` có phần văn xuôi chứa một path glob nhưng có ít hơn ~15 từ giải thích sẽ bị gắn cờ. Một claim component bắt buộc phải nói rõ component đó *chịu trách nhiệm về điều gì*, vốn là phần mà lệnh `ls` không thể nói cho bạn biết.
21. **Mùi dữ kiện công nghệ (Stack-fact smell).** Bất kỳ văn xuôi của claim nào chứa mẫu phiên bản (`\d+\.\d+`) đứng cạnh tên một package sẽ bị gắn cờ: phiên bản nằm trong lockfile, và `derived/inventory.json` đã báo cáo chúng rồi. (Quy tắc của BMAD: "`Stack` chỉ là một hạt giống; mã nguồn sở hữu điều này một khi nó tồn tại.")
22. **Claim mồ côi (Orphan claim).** Một claim không có `governs` nào trỏ tới, không có tham chiếu ngược `forge:<ID>` ở đâu, và chưa từng được trích dẫn bởi `impact.md` của bất kỳ change nào trong N thay đổi gần nhất (mặc định 20) sẽ bị gắn cờ để review. **Không phải để xóa** — xem §10 — nhưng một claim không có thứ gì tham khảo đến thì hoặc là bị đặt sai chỗ hoặc thực sự đã chết, và cả hai trường hợp đều xứng đáng được xem xét lại.

---

## 8. Khả năng truy vết mà không cần Database

### 8.1 Cơ chế: Quy ước ID + grep + một chỉ mục được sinh tự động

Tệp `derived/trace.json` là một build artifact, không bao giờ là nguồn chân lý. Nó được tính toán lại từ bốn đợt quét xác định:

| Đợt quét | Thu hoạch được |
|---|---|
| Các tệp Claim | các ID claim, `governs`, `since`, `anchors`, `evidence` |
| Các tệp ADR | các ID ADR, `supersedes`, các ID claim mà chúng tham chiếu |
| Thư mục `changes/**` (active + archive) | các ID change, các delta `REQ-*`, các ID task, các ID claim được trích dẫn trong `impact.md` |
| Code và Tests | các tham chiếu ngược trong comment `forge:<ID>`; tên bài test; các chú thích `@covers REQ-*` / `@covers INV-*` |

Toàn bộ chỉ mục chỉ là vài trăm dòng code quét tệp. Không có migration schema, không có server, và không có trạng thái nào có thể bất đồng với repository, bởi vì nó được tạo lại từ chính repository.

### 8.2 Quy ước duy nhất giúp nó hoạt động: `@covers`

Một bài test khai báo những gì mà nó giải tỏa, ngay trong tên test hoặc trong một comment liền kề:

```ts
// @covers INV-7 REQ-refunds-3
it('rejects a refund exceeding the remaining captured balance', () => { … })
```

```python
def test_refund_cannot_exceed_capture():  # @covers INV-7 REQ-refunds-3
    ...
```

Lệnh `forge sync tests` trích xuất những thông tin này vào `derived/tests.json`. Quy ước đơn giản này giúp những điều sau đây trở nên hoàn toàn xác định và trả lời phần lớn mục §11 của bản tóm lược:

| Câu hỏi | Câu trả lời |
|---|---|
| Yêu cầu nào đã dẫn đến đoạn code này? | `grep -r "forge:REQ-refunds-3"`, cộng với bản đồ ngược của `trace.json` |
| Task nào triển khai yêu cầu này? | các dòng task trong `tasks.md` mang thẻ `[REQ-refunds-3]`; `trace.json` ánh xạ chúng |
| Bài test nào xác minh yêu cầu này? | bản đồ ngược của `@covers` |
| Task này ảnh hưởng đến component kiến trúc nào? | các đường dẫn tệp của task ∩ các path glob của `CMP-` |
| Những bất biến nào bị ảnh hưởng? | các tệp bị thay đổi ∩ các neo của claim ("tập hợp chạm-claim", §9.2) |
| Bản ADR nào giải thích cho quyết định này? | trường `since:` của claim → ADR, và chuỗi `supersedes` của ADR |
| Tài liệu nào bắt buộc phải thay đổi vì đợt triển khai này? | **tập hợp chạm-claim trừ đi những gì `impact.md` đã giải trình** — xem §9.2 |

### 8.3 Những gì chủ ý *không* truy vết

Truy vết từng dòng code cụ thể tới các requirement. Việc yêu cầu các comment `forge:REQ-*` trên từng dòng code triển khai là có thể làm được nhưng tính kỷ luật chắc chắn sẽ bị suy thoái theo thời gian, và một hệ thống truy vết bị suy thoái còn tệ hơn việc không có truy vết vì nó tạo cảm giác an tâm giả tạo rằng mọi thứ đã hoàn chỉnh. Chúng ta truy vết ở mức độ chi tiết: **tệp ↔ claim** (thông qua các neo và glob của component) và **test ↔ requirement/invariant** (thông qua `@covers`), và chúng ta chấp nhận rằng câu hỏi "dòng code nào triển khai FR-3" là không thể trả lời tuyệt đối. Sự đánh đổi đó là có chủ đích; xem Q5 trong [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).

---

## 9. Cơ chế cập nhật: Tri thức thay đổi như thế nào

### 9.1 Hai, và chỉ hai, con đường hợp pháp

```
                             ┌──────────────────────────────────────────┐
  một change được hoàn thành →│ forge sync  (gập archive + neo lại)      │ → tri thức được cập nhật
                             └──────────────────────────────────────────┘
                             ┌──────────────────────────────────────────┐
  phát hiện có độ lệch     →│ forge drift resolve --verdict …          │ → tri thức được cập nhật
                             └──────────────────────────────────────────┘
```

Tuyệt đối không có con đường thứ ba. Cụ thể, không có lệnh "cập nhật tài liệu", và không có phase nào mà agent được yêu cầu "hãy sửa tài liệu cho khớp với code". Sự vắng mặt đó là một tính năng.

### 9.2 Quy tắc chạm-claim (The claim-touch rule) — Cơ chế thực thi cốt lõi

Đây là cơ chế giúp câu hỏi "tài liệu nào bắt buộc phải thay đổi?" có thể tính toán được, và nó là mảnh ghép mà tôi không tìm thấy ở bất kỳ đâu trong tài liệu tham chiếu.

Đối với một change có git diff `D`:

```
claim_touch_set(D) = { claim | bất kỳ neo nào của claim phân giải tới một tệp trong D }
                   ∪ { claim | bất kỳ path glob CMP- nào của claim khớp với một tệp trong D }
                   ∪ { claim | bất kỳ artifact bằng chứng nào của claim nằm trong D }
```

Tệp `impact.md` bắt buộc phải giải trình **tất cả** các thành viên của tập hợp đó, dưới chính xác một tiêu đề:

```markdown
## Claims touched

### Unaffected
- CMP-payments — tệp mới nằm bên trong ranh giới component hiện có; trách nhiệm không đổi
- CON-capture — từ vựng không thay đổi

### Updated
- INV-7 — giới hạn hiện tích lũy qua các lần hoàn tiền một phần (trước đây là theo từng lần hoàn)

### Superseded
- ARC-3 → ADR-0021 — domain hiện có thể đọc cache projection; ARC-3 được thay thế bởi ARC-9
```

Lệnh `forge check` tính toán tập hợp này và **chặn (blocks)** nếu có bất kỳ thành viên nào chưa được giải trình. Nó cũng chặn nếu một tệp claim bị sửa đổi trong git diff nhưng claim đó không xuất hiện dưới mục `Updated` hoặc `Superseded`, và nếu một claim xuất hiện dưới mục `Superseded` mà không có một ADR hiện hữu đi kèm.

Các hệ quả cần được nói thẳng:

- Agent không thể âm thầm thay đổi hành vi mà một invariant đang ràng buộc, bởi vì invariant đó nằm trong tập chạm và đòi hỏi phải có một câu giải trình.
- Agent không thể âm thầm chỉnh sửa một claim, bởi vì việc sửa claim sẽ đưa nó vào tập chạm *và* đòi hỏi phải nằm dưới một tiêu đề giải trình.
- Mục "Unaffected" là rẻ nhưng không miễn phí: nó tốn một câu giải thích trung thực cho mỗi claim, đó là mức giá hợp lý. Đây cũng chính là áp lực giúp giữ số lượng claim ở mức thấp — mỗi claim đều đánh một khoản "thuế" lên mọi thay đổi chạm vào các tệp của nó. **Một kho lưu gồm 40 claim chất lượng có giá trị hơn nhiều so với 400 claim, và quy tắc này làm cho điều đó trở nên đúng đắn về mặt kinh tế thay vì chỉ là lời khuyên mang tính lý thuyết.**

### 9.3 Lệnh `forge sync` tại thời điểm lưu trữ (Archive time)

Khi một change được đưa vào lưu trữ, lệnh `forge sync` thực hiện tuần tự các bước sau, từ chối ngay ở thất bại đầu tiên:

1. **Gập các delta spec** vào các spec năng lực vĩnh viễn — cơ chế hợp nhất xác định ADDED/MODIFIED/REMOVED/RENAMED của OpenSpec, kèm xác thực trước khi ghi của spec được dựng lại.
2. **Áp dụng các chỉnh sửa claim đã khai báo** từ `impact.md`: các claim `Updated` đã được chỉnh sửa trong cây thư mục làm việc (do change viết ra); `sync` xác minh rằng mỗi claim đều có mục tương ứng trong `impact.md` và, đối với các loại kiến trúc/phá vỡ giao diện, phải có một bản ADR đi kèm.
3. **Neo lại (Re-anchor)**: đối với mỗi claim trong tập chạm, đóng dấu lại `@sha` vào commit merge. Đây là thời điểm duy nhất mốc "verified as of" tiến về phía trước, và nó tiến về phía trước *chỉ bởi vì* con người đã giải trình cho claim đó.
4. **Tái tạo `derived/`** và dựng lại `trace.json`.
5. **Chạy lại `forge drift`**; bất kỳ độ lệch nào mới được phát hiện sẽ được ghi thêm vào `DRIFT.md` dưới trạng thái mở.
6. **Từ chối thực hiện** nếu: có bất kỳ `REQ-*` nào trong change không có bài test `@covers` đang pass; có bất kỳ thành viên chạm-claim nào chưa được giải trình; `DEBT.md` có các mục mở không có miễn trừ; một claim bị sửa đổi nhưng thiếu ADR bắt buộc.

Bước 3 là mấu chốt. Trong mọi hệ thống khác, mốc "verified as of" hoặc là không tồn tại hoặc được đóng dấu tự động bởi một tiến trình chạy định kỳ — điều đó đồng nghĩa với việc nó chẳng chứng nhận được điều gì cả. Ở đây nó chỉ có thể tiến về phía trước thông qua một change đã được con người giải trình hoặc một phán quyết độ lệch đã được con người ghi nhận.

### 9.4 Ai có quyền ghi cái gì

| Artifact | Bên ghi | Có thể sửa tay? |
|---|---|---|
| `OVERVIEW.md`, các tệp claim, các ADR | con người, hoặc agent khi có sự phê duyệt | Có — đây là quy trình viết tài liệu có review thông thường |
| `derived/**` | chỉ lệnh `forge sync` | **Không** — được kiểm tra tự động |
| `DRIFT.md` | `forge drift` ghi thêm; `forge drift resolve` đóng mục | Chỉ thông qua các lệnh |
| `candidates/**` | các phase bootstrap / investigate | Có |
| `trace.json` | `forge sync` | **Không** |

**Ghi chú về phương án thay thế đã bị từ chối.** Tệp append-only `.memlog.md` + artifact phái sinh của BMAD rất thanh nhã và tôi đã nghiêm túc cân nhắc nó (RESEARCH.md §5.2). Bị từ chối đối với MVP: nó nhân đôi số lượng artifact, làm cho `git blame` trên tài liệu đọc được trở nên vô dụng, và vấn đề lệch khi merge mà nó giải quyết là bài toán nhiều người cùng ghi mà chúng ta không gặp phải với một lập trình viên và một agent. Chuỗi ADR (`supersedes`) đã cung cấp cho chúng ta xuất xứ của các quyết định, vốn là phần thực sự cần đến nó. Xem xét lại nếu bài toán nhiều người cùng ghi trở thành hiện thực — Q6 trong [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).

---

## 10. Chống tạo nhiễu, và chống tỉa bớt quá tay

Cả hai chiều hướng thất bại đều là có thật. Tài liệu do AI sinh ra thì phình to vô tội vạ; các đợt dọn dẹp do AI dẫn dắt thì lại làm sạch bách tri thức quý báu. Các biện pháp đối phó được thiết kế bất đối xứng có chủ đích.

### 10.1 Chống phình to (Anti-bloat)

| Cơ chế | Tác động |
|---|---|
| **Tiêu chí kết nạp** — chỉ lưu những gì không thể đọc ra từ code chuẩn mực | Quy tắc có đòn bẩy cao nhất. Được áp dụng khi viết và khi review |
| **Yêu cầu bắt buộc phải có neo** | Một claim không có neo không thể được ghi lại (ngoại trừ `CST-`/`CON-`), vì vậy các claim mơ hồ không có nơi để tồn tại |
| **Ngân sách dòng nạp-liên-tục, không bao giờ nâng lên** | Ép buộc sự ưu tiên; vượt ngân sách là một lỗi chỉ có 2 cách sửa hợp lệ |
| **Khoản thuế chạm-claim** (§9.2) | Mỗi claim tốn một câu giải thích trên mọi change chạm vào tệp của nó. Các claim giá trị thấp sẽ trở nên đắt đỏ một cách rõ rệt |
| **Các linter chống nhiễu** (§7.3) | Bắt 4 hình thái cụ thể mà tài liệu do AI sinh ra thường mắc phải |
| **Giới hạn số lượng claim khi bootstrap** (mặc định 40) | Ngăn chặn tình trạng tràn ngập ngay từ ngày đầu; xem phase bootstrap trong [WORKFLOW.md](WORKFLOW.md) |
| **Ưu tiên một kiểm tra tự động hơn một quy tắc văn xuôi** | Quy tắc của BMAD: nếu một rule lint có thể thực thi được nó, claim sẽ chuyển thành mang bằng chứng hoặc biến mất |

### 10.2 Chống tỉa bớt quá tay (Anti-over-pruning)

Được tiếp thu gần như nguyên văn từ `project-context` của BMAD, vì đây là chính sách được lập luận xuất sắc nhất trong tài liệu tham chiếu. Một claim chỉ có thể bị **xóa hoặc hủy bỏ (retired)** dựa trên một trong bốn căn cứ:

1. **Lỗi thời hoặc sai lệch** — đối tượng tham chiếu đã biến mất, hoặc nó chưa từng đúng. Bằng chứng được nêu tên cụ thể.
2. **Được thực thi bằng cơ học** — một kiểm tra hiện tại đã phát hiện chính xác vi phạm mà claim nêu tên. (Một công cụ chỉ đơn thuần đề cập cùng chủ đề thì không được tính.) Claim được retire *và* bài kiểm tra được ghi nhận lại.
3. **Có hại hoặc mâu thuẫn** — nó trỏ vào sai thứ, hoặc nó mâu thuẫn với một claim đang hiệu lực và bị thua trong quá trình đối soát.
4. **Con người đã phê duyệt việc xóa bỏ cụ thể này**, được hỏi dưới dạng một mục riêng biệt.

Và những điều sau đây dứt khoát **không** phải là căn cứ: tính ngắn gọn; dạo gần đây không thấy cái gì bị fail; "agent có thể tự suy ra được"; và — điều nguy hiểm nhất làm rỗng các tệp tài liệu tốt — "nó có thể tự khám phá được ở đâu đó trong repository".

Lệnh `forge retire <ID> --ground <1-4> --evidence <text>` ghi nhận căn cứ vào trong claim (`status: retired`) và trong commit. Căn cứ 1–3 agent có thể tự thực hiện; căn cứ 4 bắt buộc phải có con người duyệt. Các claim đã retire vẫn nằm lại trong tệp, bị loại khỏi các kiểm tra và ngân sách dòng, để lịch sử về những gì chúng ta từng tin tưởng không bị mất đi.

### 10.3 Giao thức review khi ghi tri thức

Tiếp thu từ OpenHands: trước khi ghi vào kho lưu trữ, agent **bắt buộc phải liệt kê chính xác các claim mà nó đề xuất thêm mới hoặc sửa đổi, kèm loại và văn xuôi của chúng, và chỉ ghi những gì đã được phê duyệt.** Không phải là bản tóm tắt ý định — mà là văn bản nguyên văn. Một lần tương tác duy nhất, và nó tạo ra sự khác biệt giữa một kho lưu trữ được tuyển chọn cẩn thận và một kho lưu trữ bị bồi tụ rác.

---

## 11. Ví dụ thực tế hoàn chỉnh: Kịch bản hoàn tiền trong bản tóm lược

**Hiện trạng repository.** Thư mục `docs/system/` chứa 31 claim, trong đó có `CMP-payments`, `CMP-orders`, `CON-capture`, `INV-7` (khoản hoàn tiền ≤ khoản thu), `ARC-3` (domain không được phụ thuộc vào transport hay persistence), `API-post-refunds` chưa có (chưa có endpoint hoàn tiền), `DAT-4` (quy tắc định danh đơn hàng/thanh toán).

**Yêu cầu.** "Thêm tính năng hỗ trợ hoàn tiền cho đơn hàng (Add refund support to orders)."

Phase **investigate** đọc `derived/inventory.json`, `deps.json`, `api-surface.json`, sau đó grep các path glob của `CMP-payments` và `CMP-orders`. Nó đọc `CON-capture`, `INV-7`, `DAT-4`, `ARC-3` — bốn claim, ~40 dòng văn bản — thay vì phải đọc một tài liệu kiến trúc 3.000 dòng. Bất kỳ điều gì nó tìm hiểu được mà chưa phải là một claim và không thể phái sinh tự động sẽ được đưa vào `candidates/refunds.md` với `status: proposed` và một mức độ confidence.

Phase **spec** tạo ra các yêu cầu delta đối chiếu với các năng lực `payments` và `orders`: `REQ-refunds-1..5`, mỗi yêu cầu có các khối `#### Scenario:` dưới dạng WHEN/THEN. `forge check` xác minh cấu trúc tiêu đề, ≥1 scenario cho mỗi yêu cầu, và không còn `[NEEDS CLARIFICATION]`.

Phase **impact** — kernel tính toán bán kính ảnh hưởng ứng viên: các tệp khớp với glob của `CMP-payments` / `CMP-orders`, các phụ thuộc ngược từ `deps.json`, và tập hợp chạm-claim. Agent chọn lọc và sắp xếp nó vào `impact.md`:

```
Claims touched
  Unaffected:  CMP-orders, CON-capture, DAT-4
  Updated:     INV-7 (giới hạn tích lũy qua các lần hoàn tiền một phần)
  New:         API-post-refunds, INV-12 (khoản hoàn tiền có tính lũy thừa theo idempotency-key)
  At risk:     ARC-3 (thiết kế đề xuất đọc sổ cái thanh toán trực tiếp từ tầng domain)
```

Mục `At risk` trên `ARC-3` chính là thứ ép buộc bước tiếp theo: hoặc thiết kế phải thay đổi để tôn trọng quy tắc, hoặc bắt buộc phải có một bản ADR. **Đây chính là lúc harness phát huy tối đa giá trị của nó** — xung đột nổi lên từ trước khi có bất kỳ dòng code nào tồn tại, bởi vì claim đã được neo vào `src/domain/` và bản thiết kế chạm vào khu vực đó.

Phase **design** (bắt buộc: thay đổi là track C vì nó chạm vào một claim `ARC-` và thêm một public API) ghi nhận quyết định giữ việc đọc sổ cái nằm phía sau một port, do đó `ARC-3` được bảo toàn nguyên vẹn. Không cần viết ADR. Nếu quyết định đi theo hướng ngược lại, `forge check` sẽ từ chối chuyển sang phase `tasks` cho đến khi `ADR-0021` tồn tại.

Phase **analyze** — kiểm tra xác định: mọi `REQ-refunds-*` có ≥1 task; không có task nào thiếu requirement; không có placeholder; tập chạm-claim được giải trình trọn vẹn; rule của `ARC-3` vẫn hiện diện. LLM review: `REQ-refunds-2` và `REQ-refunds-4` có phân biệt rõ ràng không? `INV-12` có kiểm thử được như đã phát biểu không?

Phases **tasks / implement / test** — TDD theo từng task; mỗi test được gắn thẻ `@covers REQ-refunds-N` và, đối với các invariant, gắn thẻ `@covers INV-7` / `@covers INV-12`.

Phase **verify** — build, typecheck, lint, tests; kiểm tra tuân thủ `deps.cjs` (để `ARC-3` được chứng minh lại); chạy `oasdiff` trên hợp đồng được tạo lại cho `API-post-refunds`; mọi `REQ-refunds-*` đều có bài test `@covers` đang pass; `DEBT.md` trống; `forge drift` sạch sẽ.

Phases **sync / converge** — các bản delta được gập vào các spec vĩnh viễn; văn xuôi của `INV-7` được cập nhật (đã được viết trong change, giải trình trong `impact.md`); `API-post-refunds` và `INV-12` được thêm mới kèm các neo và bằng chứng; `@sha` của mọi claim bị chạm tịnh tiến tới commit merge; `derived/` và `trace.json` được tạo lại; change được đưa vào lưu trữ.

**Sáu tháng sau**, ai đó thay thế sổ cái bằng Redis. Lệnh `forge drift` báo cáo `INV-7` và `ARC-3` bị lỗi thời (stale) kèm diff của fingerprint; quy tắc phụ thuộc của `ARC-3` *bị thất bại (fail)*, đây là một lỗi chặn (blocking error), không phải một cảnh báo. Sổ cái đề xuất phán quyết V3 kèm lập luận logic. Con người ghi nhận `--verdict V3 --adr 0034`, hoặc sửa lại code. **Tài liệu kiến trúc tuyệt đối không bao giờ bị âm thầm viết lại thành Redis.**

---

## 12. Các phi mục tiêu có chủ ý (Deliberate non-goals)

| Không xây dựng | Lý do |
|---|---|
| Một đồ thị tri thức (Knowledge graph) | Của GSD đã trở thành cách biểu diễn thứ tư mang theo sự mục rữa riêng. Những mối liên kết không thể kiểm chứng là những món nợ. Bộ đôi `governs` + `trace.json` đã bao phủ 90% trường hợp hữu ích |
| Embeddings / tìm kiếm ngữ nghĩa trên kho lưu | 40 claim hoàn toàn nằm gọn trong một lệnh grep. Chất lượng truy xuất không phải là điểm nghẽn; tính đáng tin cậy mới là điểm nghẽn |
| Đồ thị code / chỉ mục SCIP | Tìm kiếm của host agent cộng với tree-sitter cộng với công cụ phụ thuộc của hệ sinh thái là đủ dùng ở quy mô cá nhân. Chỉ xem xét lại khi grep thực sự thất bại rõ rệt |
| Các sơ đồ kiến trúc do LLM sinh ra làm tri thức | Một sơ đồ không thể định địa chỉ riêng, không thể neo, không thể kiểm tra tự động. Sơ đồ Mermaid bên trong văn xuôi của claim chỉ dùng để minh họa; nó không bao giờ là bản thân claim |
| Tỷ lệ phần trăm "độ bao phủ tài liệu" | Mời gọi sự thao túng chỉ số và khuyến khích số lượng. Tỷ lệ `enforced`/`asserted` mới là thước đo trung thực |
| Tự động trích xuất claim từ các commit | Tạo ra tiếng ồn nghe-có-vẻ-đúng ở quy mô lớn. Luôn luôn phải qua các ứng viên + sự phê chuẩn của con người |
| Tri thức xuyên suốt nhiều repo / toàn tổ chức | Nằm ngoài phạm vi của một harness cá nhân. Định dạng claim có thể mở rộng được, nhưng bộ công cụ thì không |
