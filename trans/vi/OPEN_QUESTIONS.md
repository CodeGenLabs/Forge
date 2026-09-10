# OPEN_QUESTIONS.md — Các câu hỏi chưa giải quyết

Các câu hỏi chưa có lời giải đáp ngã ngũ trong thiết kế. Mỗi câu hỏi đều mang các phần: tại sao nó quan trọng, các phương án lựa chọn, một khuyến nghị (nếu tôi có), và **những bằng chứng nào vẫn còn thiếu** — bởi vì một số câu hỏi trong số này không thể giải quyết bằng cách đọc thêm tài liệu, mà chỉ có thể giải quyết bằng cách chạy thử nghiệm thực tế.

Mức độ ưu tiên: **P0** = bắt buộc phải được trả lời trước khi viết MVP · **P1** = bắt buộc phải được trả lời trong quá trình làm MVP · **P2** = chủ ý hoãn lại sau.

---

## Q1 — Liệu bất kỳ điều nào trong số này có thực sự cải thiện kết quả? **P0 (về sự trung thực), P1 (về phép đo lường)**

**Tại sao quan trọng.** Đây là câu hỏi mà toàn bộ đề xuất này dựa vào, và tài liệu tham chiếu không cung cấp bằng chứng xác đáng cho bất kỳ chiều hướng nào. Không có dự án nào trong số 6 dự án công bố một đánh giá thực nghiệm về chính phương pháp luận của họ. Những con số cụ thể duy nhất ở gần không gian này thuộc về mini-SWE-agent — một vòng lặp ~200 dòng code *không hề* có phương pháp luận, không spec, không tri thức kiến trúc — nhưng lại báo cáo kết quả >74% trên SWE-bench Verified. Hoàn toàn có khả năng là quy trình mang lại độ tin cậy trên các codebase tồn tại lâu đời và chẳng mang lại giá trị gì trên các tác vụ có phạm vi rõ ràng, và cũng có thể nó chẳng mang lại giá trị gì cả.

**Các phương án.**

- **A. Mặc định là có giá trị, cứ xây dựng, không bao giờ đo lường.** Cách mà mọi dự án tham chiếu đã làm.
- **B. Xây dựng MVP, sau đó chạy so sánh ghép cặp (paired comparison)** trên các thay đổi thực tế trong một repository: cùng một yêu cầu, một lần chạy có harness và một lần không có, so sánh tỷ lệ phải làm lại (rework rate), các phát hiện khi review, và thời gian để đạt trạng thái test xanh (time-to-green).
- **C. Gắn thiết bị đo lường (instrument) ngay từ ngày đầu**: `verification.json` và các file trajectory đã ghi nhận đủ dữ liệu để tính toán số bước thực hiện cho mỗi thay đổi, chi phí, thời gian thực (wall-time), số lần xác minh thất bại trước khi pass, và quy kết nguồn gốc lỗi sau khi merge.
- **D. Không xây dựng gì cả; chỉ sử dụng tính kỷ luật của mini-SWE-agent và không gì khác.**

**Khuyến nghị. C, sau đó đến B.** Phương án C gần như miễn phí vì các artifact đã tồn tại sẵn — chỉ cần thêm lệnh `forge stats` để tổng hợp chúng. Phương án B đòi hỏi tính kỷ luật nhưng chỉ cần ~20 thay đổi là đã đủ mang tính gợi mở. Dứt khoát từ chối phương án A: một harness không thể chứng minh giá trị của chính nó chỉ là một hệ thống niềm tin giáo điều.

**Bằng chứng còn thiếu.** Bất kỳ so sánh có đối chứng nào, ở bất kỳ đâu, giữa quy trình agent định hướng bởi spec (spec-driven) với một vòng lặp trần trụi trên một codebase *đang được duy trì liên tục* (SWE-bench chỉ đo lường các bản vá lỗi đơn lẻ trên các repo mà agent không phải duy trì lâu dài — sai định dạng đối với câu hỏi này).

---

## Q2 — Liệu các neo (anchors) có sống sót qua các đợt tái cấu trúc thực tế? **ĐÃ TRẢ LỜI 2026-09-10 — phần lớn là có**

> **Kết luận giải quyết.** Đã đo lường trong [docs/measurements/M1-anchor-stability.md](docs/measurements/M1-anchor-stability.md):
> 600 commit được phát lại (replay) trên 3 repository kèm theo một thí nghiệm gây nhiễu có đối chứng (perturbation experiment).
> Khuyến nghị **A + D** đã được triển khai — neo đường dẫn+symbol (path+symbol) kết hợp theo dõi đổi tên của git, cộng với việc phân tách `shifted`/`stale` — và các kết quả gây nhiễu đã loại bỏ rủi ro đối với các trường hợp mang tính cơ học (định dạng, sửa comment, kiểu dấu ngoặc kép, di chuyển tệp thuần túy). Phương án **C** (neo cấp component) là không cần thiết và không được triển khai. Phương án **B** (định vị theo địa chỉ nội dung - content-addressed relocation) *đã* được triển khai, nhưng không phải vì lý do ban đầu được đề xuất: nó hóa ra lại cần thiết như một phương án dự phòng khi tính năng phát hiện đổi tên của git đầu hàng trước một đợt di chuyển có độ tương đồng thấp, điều mà phép đo lường đã phát hiện và sau đó đã xử lý triệt để (0.61% → 0.00%). Mục đích sử dụng dự kiến khác của nó, cơ chế bảo vệ `forge reanchor`, vẫn đang chờ kho lưu trữ claim ở M0.
>
> Ba phần tồn đọng khiến câu hỏi này chưa thể khép lại hoàn toàn:
> 1. Các đợt tái cấu trúc trung tính về mặt ngữ nghĩa (trích xuất biến, sắp xếp lại các câu lệnh độc lập) không có cơ sở chân lý thực nghiệm cơ học và bị loại trừ khỏi tỷ lệ đo lường, do đó tỷ lệ dương tính giả thực tế sẽ cao hơn mức được báo cáo một khoảng chưa xác định.
> 2. Chỉ có các khai báo có phần thân (body) mới bị gây nhiễu; các interface, type alias và khai báo `const` chỉ mới được bao phủ bởi các unit test.
> 3. Ba ngôn ngữ, ba repository, shallow clones, chỉ chạy trên nhánh chính (mainline).
>
> Câu hỏi và các phương án ban đầu được giữ lại bên dưới vì các phần tồn đọng vẫn đang tiếp diễn.

### Câu hỏi ban đầu **P0**

**Tại sao quan trọng.** Toàn bộ cơ chế phát hiện lỗi thời đều dựa trên `path#Symbol@sha` + dấu vân tay AST (AST fingerprints) đã được chuẩn hóa. Một thao tác đổi tên, di chuyển tệp, hoặc tách hàm (extract-method) sẽ đánh dấu mọi neo trên symbol bị ảnh hưởng là lỗi thời (stale). Nếu một đợt tái cấu trúc thông thường tạo ra 15 mục sai lệch giả mạo, sổ cái sẽ trở thành một mớ nhiễu và bị phớt lờ — và một sổ cái bị phớt lờ còn tồi tệ hơn việc không có sổ cái nào, vì nó tạo cảm giác an tâm giả tạo về độ bao phủ. Fiberplane nêu tên hạn chế này nhưng không giải quyết nó.

**Các phương án.**

- **A. Neo path+symbol kết hợp phát hiện đổi tên của git** khi phân giải baseline (`git log --follow`, `--find-renames`). Xử lý được các trường hợp di chuyển tệp thuần túy và đổi tên không làm thay đổi ngữ nghĩa.
- **B. Neo định vị theo nội dung (Content-addressed anchors)** — neo trực tiếp vào chính fingerprint, và định vị symbol bằng cách tìm kiếm fingerprint khớp tại HEAD. Sống sót hoàn toàn qua các lần di chuyển tệp; thất bại khi code có bất kỳ thay đổi nào, vốn là trường hợp mà chúng ta đằng nào cũng muốn phát hiện.
- **C. Neo thô hơn (Coarser anchors)** — neo vào component (một đường dẫn glob) thay vì một symbol. Ít dương tính giả hơn nhiều, nhưng độ chính xác kém hơn nhiều; thực chất là cách tiếp cận cấu trúc của GSD.
- **D. Chính sách dung sai (Tolerance policy)** — coi "fingerprint thay đổi nhưng *signature* của symbol không đổi" là một tín hiệu yếu hơn (`shifted`) so với việc thay đổi signature (`stale`), và chỉ mặc định hiển thị `stale`.

**Khuyến nghị. A + D, kết hợp B làm công cụ hỗ trợ re-anchor.** Lệnh `forge reanchor` chỉ chấp nhận đóng dấu lại (restamp) khi fingerprint khớp theo ánh xạ đổi tên của git — miễn phí khi không có gì thay đổi về ngữ nghĩa, và không thể thực hiện khi có thay đổi. Thêm sự phân biệt `shifted`/`stale` để việc chỉnh sửa chỉ ở phần thân hàm sẽ bớt gây ồn ào hơn việc thay đổi signature. Từ chối C: mất độ chính xác ở cấp symbol đồng nghĩa với việc mất toàn bộ lợi thế của cơ chế này so với GSD.

**Bằng chứng thu được.** Cả hai thí nghiệm đều đã được chạy (xem phần kết luận giải quyết ở trên). Hai phát hiện đã làm thay đổi thiết kế thay vì chỉ đơn thuần xác nhận nó: `shifted` đã phải trở thành một trạng thái hạng nhất vì các chỉnh sửa chỉ ở phần thân chiếm tới 79% tổng số phán quyết không-tươi-mới, và `coarse` đã phải trở thành một cờ (flag) thay vì một trạng thái. Ba khiếm khuyết trong fingerprint đã được phát hiện bởi bộ khung gây nhiễu, tất cả chúng đáng lẽ sẽ nổi lên thành các tiếng ồn trong sổ cái thay vì làm ứng dụng bị crash.

**Bằng chứng còn thiếu.** Tỷ lệ đối với các đợt tái cấu trúc trung tính về mặt ngữ nghĩa, vốn đòi hỏi con người phải gắn nhãn thủ công; và bất kỳ ngôn ngữ nào nằm ngoài ba ngữ pháp hiện có.

---

## Q3 — Liệu việc giải trình "Unaffected" (Không ảnh hưởng) có biến thành hành vi phê duyệt hình thức? **P0**

**Tại sao quan trọng.** Quy tắc chạm-claim (SYSTEM_KNOWLEDGE.md §9.2) là cơ chế thực thi cốt lõi của toàn bộ thiết kế: mọi claim có neo hoặc glob giao cắt với git diff đều phải được giải trình trong `impact.md`. Nếu câu trả lời trung thực thường là "unaffected", agent sẽ học được thói quen đưa ra câu "unaffected — no behavioural change" cho mọi thứ, và việc kiểm tra biến thành một thủ tục hình thức tốn token mà không mang lại giá trị gì. Đây chính là sự suy thoái khiến cho việc tuân thủ kiểu tích ô vuông (checkbox compliance) trở nên vô giá trị.

**Các phương án.**

- **A. Chấp nhận nó.** Ngay cả một danh sách mang tính hình thức cũng đưa các ID của claim vào trong ngữ cảnh, điều này vẫn có giá trị nhất định.
- **B. Yêu cầu lý do biện minh có tính phân hóa** — từ chối lý do `Unaffected` nếu nó có cấu trúc văn bản tương tự một mục khác, hoặc dưới N từ, hoặc không nêu tên một điểm cụ thể nào về claim đó.
- **C. Giảm quy mô tập hợp chạm (touch set)** — chỉ những claim có neo giao cắt với git diff *và* có loại thuộc {invariant, architecture, interface, datum} mới bắt buộc phải giải trình; các claim loại component và concept chỉ được liệt kê để lấy ngữ cảnh.
- **D. Lấy mẫu ngẫu nhiên (Sample)** — yêu cầu giải trình đầy đủ cho một tập hợp con ngẫu nhiên cộng với tất cả các claim thuộc loại quan trọng cao, để thói quen lười biếng không thể hình thành quanh một tập hợp con có thể dự đoán trước.
- **E. Giữ số lượng claim ở mức thực sự thấp** để danh sách chỉ có từ 3–5 mục, khi đó việc đọc nó sẽ ít tốn kém hơn việc tìm cách lách luật.

**Khuyến nghị. C + E, kết hợp kiểm tra độ tương đồng của B như một linter chi phí thấp.** C hướng việc giải trình vào những loại claim mà việc sai sót sẽ phải trả giá đắt. E là câu trả lời thực chất, và đó là lý do tại sao các ngân sách trong CONSTITUTION.md X và XIV tồn tại: **quy tắc chạm-claim chỉ bền vững nếu kho lưu trữ giữ được quy mô nhỏ, và chính quy tắc này làm cho việc giữ kho lưu trữ nhỏ trở nên hợp lý về mặt kinh tế.** Từ chối D — những nghĩa vụ không thể dự đoán trước sẽ rèn luyện tính né tránh thay vì sự cẩn trọng.

**Bằng chứng còn thiếu.** Phân phối kích thước thực tế của tập hợp chạm trên các thay đổi thực tế. Có thể đo lường sau ~10 thay đổi với MVP.

---

## Q4 — Ngân sách nạp-liên-tục (always-loaded budget) bao nhiêu là hợp lý? **P1**

**Tại sao quan trọng.** Nguyên tắc X nghiêm cấm việc nâng ngân sách, điều này làm cho con số ban đầu mang tính quyết định. 400 dòng là phép ngoại suy của tôi từ kỷ luật ngân sách được nêu của BMAD và các tài liệu nghiên cứu về sự mục rữa ngữ cảnh (context-rot) — không phải là một số liệu đo lường thực nghiệm. Quá thấp thì agent sẽ thiếu các khái niệm nó cần và hỏi những câu không nên hỏi; quá cao thì khả năng tuân thủ chỉ dẫn sẽ suy giảm trên diện rộng, một sự suy thoái vô hình thường bị đổ lỗi nhầm cho chất lượng mô hình.

**Các phương án.**

- **A. Cố định 400 dòng** (được đề xuất ban đầu).
- **B. Dựa trên số lượng token, không dựa trên dòng** (ví dụ 6.000 tokens) — chính xác hơn, nhưng cần thêm dependency tokenizer.
- **C. Phân tầng (Tiered)**: một lõi nạp-liên-tục ~100 dòng (OVERVIEW + chỉ mục claim) cộng với việc nạp claim theo từng phase thông qua hợp đồng `reads` của DAG, hoàn toàn không có các tệp claim nạp-liên-tục riêng lẻ.
- **D. Đo lường theo từng dự án**: chạy một bộ tác vụ cố định ở nhiều mức ngân sách khác nhau và chọn điểm uốn (knee of the curve).

**Khuyến nghị. C, với A làm mức trần cho toàn bộ các tệp bắt buộc của kho lưu trữ.** DAG đằng nào cũng phân giải phần thân của claim theo từng phase — vì vậy tập hợp *nạp-liên-tục* thực sự chỉ cần `OVERVIEW.md` cộng với chỉ mục claim (chỉ gồm ID và tiêu đề), con số này gần với mức 100 dòng hơn. Điều đó biến con số 400 dòng thành ngân sách kích thước kho lưu trữ thay vì ngân sách ngữ cảnh, đó là cách sử dụng hợp lý hơn. Xem xét lại phương án B một khi đã có sẵn tokenizer vì một lý do khác.

**Bằng chứng còn thiếu.** Bất kỳ phép đo lường nào về sự suy giảm khả năng tuân thủ chỉ dẫn theo hàm số của ngữ cảnh dự án nạp-liên-tục, trên các mô hình host cụ thể mà chúng ta quan tâm. Nghiên cứu của Chroma chỉ ra hiện tượng, chứ không chỉ ra ngưỡng cụ thể.

---

## Q5 — Liệu các spec năng lực vĩnh viễn và các claim bất biến (invariants) có bị dư thừa chồng chéo? **P1**

**Tại sao quan trọng.** Thiết kế duy trì hai kho lưu trữ hành vi vĩnh viễn: các spec năng lực kiểu OpenSpec (các yêu cầu `REQ-*` kèm kịch bản) và các claim `INV-*`. Cả hai đều mô tả những điều bắt buộc phải đúng. Việc có hai kho lưu trữ các nghĩa vụ chồng chéo nhau chính xác là thất bại đa-biểu-diễn (multi-representation) mà tôi đã chỉ trích ở GSD.

**Các phương án.**

- **A. Giữ cả hai, kèm một quy tắc ranh giới sắc bén.** Một `REQ-*` là *hành vi có thể quan sát được từ bên ngoài của một năng lực*; một `INV-*` là *một đặc tính bắt buộc phải duy trì trên toàn bộ mọi hành vi*, thường không quan sát được từ bên ngoài (tính toàn vẹn tham chiếu, tính đơn điệu, tính lũy thừa - idempotency, các đồng nhất thức kế toán). Nguồn chân lý khác nhau (spec đối chiếu với tests), vòng đời khác nhau (một REQ được tạo ra bởi một thay đổi; một INV tồn tại qua nhiều thay đổi).
- **B. Gộp chung vào claims.** Biến các yêu cầu thành một loại claim (`REQ-`) và bỏ tầng spec riêng biệt. Mất đi tính năng gập lưu trữ (archive fold) mang tính xác định của OpenSpec và cách gom nhóm năng lực giúp spec dễ đọc như một tài liệu hoàn chỉnh.
- **C. Gộp chung vào specs.** Diễn đạt các invariant dưới dạng các yêu cầu kèm kịch bản. Mất đi cơ chế neo và bộ máy `enforced`/evidence, vốn là phần giúp các invariant có thể kiểm tra tự động được.

**Khuyến nghị. A, và ghi rõ quy tắc đó thành một bài test kết nạp loại claim**: "nếu điều này có thể bị vi phạm mà không một người dùng nào nhận ra, thì nó là một invariant, không phải là một requirement." Đồng thời thực thi một kiểm tra không-chồng-chéo: một `INV-` có nội dung văn xuôi diễn giải lại một `REQ-` sẽ bị coi là một vi phạm (finding).

**Bằng chứng còn thiếu.** Tần suất ranh giới này thực sự bị mơ hồ trong thực tế. Dự đoán: hiếm khi, nhưng mười thay đổi đầu tiên sẽ chứng minh điều đó.

---

## Q6 — Chỉnh sửa claim tại chỗ, hay ghi nhật ký append-only kèm render phái sinh? **P2**

**Tại sao quan trọng.** `bmad-spec` của BMAD sử dụng một tệp append-only `.memlog.md` làm chuẩn tắc với `SPEC.md` *được phái sinh ở mỗi lần chạy*, và đưa ra một lý do thuyết phục: nó cho phép nhiều tiến trình cùng ghi vào một artifact theo bất kỳ thứ tự nào mà không bị lệch khi merge (merge drift), và truy xuất nguồn gốc (provenance) là miễn phí. Thiết kế của chúng ta chỉnh sửa trực tiếp tại chỗ các claim và dựa vào git cộng với chuỗi `supersedes` của ADR để truy xuất nguồn gốc.

**Các phương án.**

- **A. Chỉnh sửa tại chỗ (In-place editing)** (được đề xuất). Đơn giản, `git blame` hoạt động trực tiếp trên tài liệu có thể đọc được, một tệp cho mỗi loại claim.
- **B. Log append-only + render phái sinh.** Không bị xung đột khi merge, lịch sử quyết định đầy đủ, nhưng nhân đôi số lượng artifact, làm cho `git blame` trên tệp đọc được trở nên vô dụng, và đòi hỏi tuyệt đối không ai được chỉnh sửa tay vào tệp render — một kỷ luật chắc chắn sẽ bị vi phạm.
- **C. Lai ghép (Hybrid)**: claim chỉnh sửa tại chỗ, cộng với một tệp append-only `docs/system/decisions/LOG.md` chứa các bản ghi quyết định một dòng mà các ADR sẽ mở rộng chi tiết.

**Khuyến nghị. A cho MVP; C nếu bài toán nhiều người ghi (multi-writer) trở thành hiện thực.** Vấn đề lệch merge mà phương án B giải quyết là bài toán của nhiều người cùng ghi, trong khi chúng ta chỉ có một lập trình viên và một agent. Chuỗi ADR đã cung cấp nguồn gốc cho phần thực sự cần đến nó. Xem xét lại nếu harness chạy nhiều agent cùng ghi tri thức đồng thời — tại thời điểm đó phương án B sẽ trở nên hoàn toàn đúng đắn.

**Bằng chứng còn thiếu.** Liệu việc ghi tri thức đồng thời có thực sự xảy ra trong quá trình sử dụng của một lập trình viên duy nhất hay không. Dự đoán là không.

---

## Q7 — Liệu grep và tầng phái sinh có đủ dùng, hay cuối cùng vẫn cần một code index? **P2**

**Tại sao quan trọng.** Thiết kế chủ ý từ chối đồ thị code (code graph), SCIP index, hoặc embeddings, dựa trên lập luận rằng bộ máy của GSD đã trở thành một cách biểu diễn thứ tư mang theo sự mục rữa của riêng nó. Sự từ chối đó là đúng ở quy mô 20k dòng code và có thể sẽ sai ở quy mô 2 triệu dòng code.

**Các phương án.**

- **A. Không bao giờ cần.** Chỉ dùng Grep + tree-sitter + công cụ phụ thuộc của hệ sinh thái ngôn ngữ.
- **B. Bổ sung SCIP khi vượt qua một ngưỡng nhất định** (kích thước repo, hoặc chi phí điều tra đo được cho mỗi thay đổi).
- **C. Bổ sung cơ chế xếp hạng tree-sitter + PageRank kiểu Aider** dưới dạng `derived/repo-map.json` — một artifact nhỏ gọn, có thể tái tạo lại được thay vì một index server thường trực. Điều này hoàn toàn phù hợp với tầng phái sinh: truy xuất nguồn gốc theo commit, tái tạo đồng nhất đến từng byte, không cần tiến trình daemon.

**Khuyến nghị. A cho MVP; C là phương án leo thang đầu tiên, không phải B.** C giữ được đặc tính rằng mọi thứ đều là văn bản có thể tái tạo kèm nguồn gốc commit; B đưa vào một bộ indexer với vòng đời phức tạp riêng của nó. Thiết lập điều kiện kích hoạt rõ ràng: nếu phase `investigate` thường xuyên vượt quá ngân sách số bước trên một repository, hãy bổ sung C.

**Bằng chứng còn thiếu.** Kích thước repository mà tại đó khả năng tìm kiếm tự thân của host agent không còn đáp ứng đủ tốt nữa. Chưa xác định được và có thể phụ thuộc vào từng host.

---

## Q8 — LLM có thể đóng góp hữu ích đến mức nào cho một phán quyết độ lệch (drift verdict)? **P1**

**Tại sao quan trọng.** Thiết kế để mô hình *đề xuất* một phán quyết (V1–V4) và con người *ghi nhận* phán quyết đó. Nhưng nghiên cứu arXiv:2604.03447 cho thấy mô hình yếu nhất chính tại điểm này — khả năng phát hiện giảm 21–43 điểm khi chỉ có phần triển khai thay đổi — và độ tự tin của nó không phân biệt được phán đoán đúng hay sai. Nếu các đề xuất phần lớn là sai, chúng còn tệ hơn việc không có đề xuất: chúng neo phán đoán của con người vào sai vị trí.

**Các phương án.**

- **A. Đề xuất một phán quyết kèm lập luận** (như thiết kế ban đầu).
- **B. Chỉ đề xuất bằng chứng, tuyệt đối không đưa ra phán quyết**: hiển thị diff của fingerprint, liệu test kiểm chứng có còn pass hay không, liệu quy tắc tuân thủ có còn pass hay không, các thông điệp commit trong phạm vi đó nói gì — và để con người tự phân loại.
- **C. Chỉ đề xuất phán quyết khi có một tín hiệu cơ học giúp làm rõ.** Nếu quy tắc hiện tại bị fail → V1 hoặc V3 (không bao giờ là V2/V4). Nếu test của invariant vẫn pass và chỉ có phần thân hàm thay đổi → nhiều khả năng là V1 hoặc do claim chưa đủ cụ thể. Nếu thay đổi đến từ một change của `forge` có kèm ADR → V3, đã được giải trình trước.
- **D. Hoàn toàn không để LLM can thiệp** vào việc xử lý độ lệch.

**Khuyến nghị. C.** Nó chỉ sử dụng mô hình ở những nơi mà một tín hiệu xác định đã thu hẹp không gian lựa chọn, đó là phạm vi duy nhất mà tài liệu nghiên cứu cung cấp cơ sở để tin cậy. *Luôn luôn* trình bày gói bằng chứng của B, và đính kèm đề xuất thu hẹp của C *khi có sẵn*. Tuyệt đối không đưa ra một phán quyết trần trụi với lập luận bằng văn xuôi mà không có tín hiệu cơ học đi kèm.

**Bằng chứng còn thiếu.** Độ chính xác của việc đề xuất phán quyết trên độ lệch thực tế, có thể đo lường một khi sổ cái có ~20 mục đã được giải quyết. Cho đến lúc đó, hãy ưu tiên định dạng của B.

---

## Q9 — Liệu `analyze` là một phase hay chỉ đơn thuần là một cổng (gate)? **P1**

**Tại sao quan trọng.** Hiện tại nó tồn tại dưới cả hai hình thức: một tập hợp các kiểm tra xác định tại `analyze:post` và một tài liệu `analysis.md`. Nếu các kiểm tra xác định là phần thực chất, thì tài liệu chỉ là một bản báo cáo không ai đọc và phase này là một thủ tục hình thức. Spec Kit biến nó thành một lệnh hoàn chỉnh với bảng phát hiện 50 dòng và một thang đo mức độ nghiêm trọng; liệu điều đó có xứng đáng với chi phí bỏ ra hay không vẫn chưa rõ ràng.

**Các phương án.**

- **A. Một phase có artifact** (như thiết kế ban đầu).
- **B. Chỉ là một cổng (Gate only)** — `forge check --scope change` chạy tại `tasks:post`, in ra các phát hiện, chặn nếu gặp CRITICAL, không ghi tệp nào. Phần review ngữ nghĩa của LLM được gộp vào phần tự review của chính phase `tasks`.
- **C. Cổng + artifact tùy chọn** — tài liệu chỉ được viết ra khi có các phát hiện tồn tại và không được sửa chữa ngay lập tức.

**Khuyến nghị. B, với lối thoát của C.** Một phase riêng biệt tạo ra một tài liệu tóm tắt lại các bài kiểm tra đã chạy thực chất là một nghi thức mang tính hình thức. Superpowers đạt được giá trị tương tự từ một checklist tự review nội dòng ("Nếu bạn tìm thấy vấn đề, hãy sửa ngay tại chỗ. Không cần phải review lại — chỉ cần sửa và đi tiếp"). Chỉ giữ lại tài liệu cho những phát hiện *được chấp nhận tạm thời thay vì được sửa ngay*, vì những trường hợp đó cần một bản ghi lưu vết.

**Bằng chứng còn thiếu.** Liệu các bài kiểm tra ngữ nghĩa của LLM có tìm thấy bất cứ điều gì mà các bài kiểm tra xác định bỏ sót trên các thay đổi thực tế hay không. Nếu không, hãy loại bỏ chúng để tiết kiệm token.

---

## Q10 — Điều gì xảy ra với các thay đổi được thực hiện bên ngoài harness? **P1**

**Tại sao quan trọng.** Các bản hotfix, commit của người khác, bot nâng cấp dependency, và việc "tôi vừa sửa nhanh trong trình soạn thảo" là điều chắc chắn xảy ra. Nếu các commit ngoài luồng này âm thầm tích lũy các neo lỗi thời và các tệp chưa được ánh xạ, lệnh `forge drift` đầu tiên sau một tuần bận rộn sẽ tạo ra một bức tường cảnh báo dày đặc và người dùng sẽ tuyên bố từ bỏ harness. Mọi kế hoạch duy trì tri thức đều chết theo cách này.

**Các phương án.**

- **A. Lượt đối soát (Reconcile pass)** — `forge reconcile <range>` phân loại các commit trong một phạm vi: commit nào đã chạm vào các neo của claim, commit nào đã thêm các tệp chưa được ánh xạ, commit nào đã thay đổi các hợp đồng giao diện. Tạo ra một loạt các mục drift với một quy trình review duy nhất.
- **B. Pre-commit / pre-push hook** chạy `forge check --scope store` (chi phí thấp) và `forge drift --changed` (cũng chi phí thấp, vì nó chỉ kiểm tra các neo trong git diff). Bắt độ lệch ngay tại khoảnh khắc nó được tạo ra, khi lý do vẫn còn nằm trong đầu người lập trình.
- **C. Chấp nhận tình trạng tồn đọng (backlog)** và dựa vào cơ chế miễn trừ của sổ cái để giữ cho các cổng kiểm soát vẫn sử dụng được.
- **D. Yêu cầu mọi thay đổi bắt buộc phải đi qua harness.** Không thực tế, và sẽ bị vi phạm ngay từ ngày đầu tiên.

**Khuyến nghị. Chủ yếu là B, dùng A làm lộ trình phục hồi.** B là sự bổ sung có giá trị cao với chi phí thấp nhất của thiết kế và là điểm tích hợp duy nhất đáng để sử dụng một hook (ARCHITECTURE.md §5.3): chỉ kiểm tra các neo bị chạm bởi git diff hiện tại là đủ nhanh để chạy trên mọi commit. A tồn tại vì B đôi khi sẽ bị người dùng bypass qua cờ `--no-verify`.

**Bằng chứng còn thiếu.** Thời gian chạy thực tế của `forge drift --changed` trên một git diff lớn. Dự kiến chỉ mất từ vài mili-giây đến vài giây; cần được xác nhận bằng thực nghiệm.

---

## Q11 — Harness nằm ở đâu, và tri thức có vượt qua ranh giới giữa các repository không? **P2**

**Tại sao quan trọng.** Kernel có thể được cài đặt toàn cục (một lệnh `forge` duy nhất trên PATH) hoặc được nhúng riêng (vendored) theo từng repository. Kho lưu trữ claim được thiết kế theo từng repository, nhưng một lập trình viên duy nhất thường tích lũy các cạm bẫy xuyên dự án ("tôi luôn viết sai cú pháp glob trong pnpm workspace") cần phải được lưu trữ ở đâu đó.

**Các phương án.**

- **A. Kernel toàn cục, cấu hình và kho lưu trữ theo từng repo** (được đề xuất). Dạng công cụ tiêu chuẩn.
- **B. Nhúng kernel riêng vào từng repo.** Đảm bảo tính tái lập, không bị lệch phiên bản, nhưng phải cập nhật N bản copy.
- **C. Kernel toàn cục + một kho lưu cạm bẫy toàn cục** được gộp vào tập hợp nạp-liên-tục.
- **D. Kernel toàn cục + chỉ dùng kho lưu trữ theo từng repo**; các bài học xuyên dự án sẽ nằm trong cấu hình agent cá nhân của chính lập trình viên, không nằm trong harness.

**Khuyến nghị. A + D.** Tri thức xuyên dự án là bài toán về sở thích cá nhân, không phải bài toán tri thức hệ thống, và việc trộn lẫn chúng sẽ phá vỡ mô hình nguồn chân lý (một cạm bẫy toàn cục không có neo nào trong repository này). BMAD cũng đi đến cùng một kết luận: các quy tắc "lặp lại trên các dự án của họ, hoặc mang tính cá nhân thay vì của nhóm, thuộc về cấu hình agent toàn cục của họ". Ghim phiên bản kernel trong `.forge/config.yaml` để repo có thể phát hiện sự lệch pha phiên bản.

**Bằng chứng còn thiếu.** Không cần; đây là một quyết định về sở thích với lập luận rõ ràng.

---

## Q12 — Các skills bắt buộc phải hoạt động trên những host nào, và với chi phí ra sao? **P1**

**Tại sao quan trọng.** Superpowers phải duy trì các file manifest plugin cho 8 môi trường runtime host (`.claude-plugin`, `.codex-plugin`, `.cursor-plugin`, `.devin-plugin`, `.hermes-plugin`, `.kimi-plugin`, `.opencode`, `.pi`) cộng với một script đồng bộ ~15.000 bytes và các bộ test suite theo từng host. Spec Kit phải duy trì các bản sao bash, PowerShell **và** Python cho mọi script. Thuế phí di chuyển (portability tax) đó rất lớn và lặp đi lặp lại.

**Các phương án.**

- **A. Một host duy nhất (Claude Code) cho v1.** Các skill dưới dạng plugin cục bộ; kernel dưới dạng CLI, vốn dĩ có tính linh động tự nhiên.
- **B. Các skill không phụ thuộc host ngay từ đầu** — chỉ là markdown thuần túy trong `.forge/skills/`, được gọi qua đường dẫn, kèm một lớp đệm (shim) mỏng theo từng host.
- **C. Hỗ trợ đa host đầy đủ.** Từ chối: đó là khoản thuế mà Superpowers phải trả, đối với một harness cá nhân thì không đáng.

**Khuyến nghị. A, nhưng cấu trúc sao cho việc chuyển sang B tốn ít chi phí nhất.** Giữ mọi skill dưới dạng markdown thuần túy không chứa cú pháp riêng của host nào, và giữ toàn bộ cơ chế logic trong kernel — một CLI có thể chạy ở mọi nơi. Khi đó việc hỗ trợ một host thứ hai chỉ là một file manifest, không phải là một đợt port code. Hệ quả quan trọng nhất: **các skill tuyệt đối không bao giờ được phụ thuộc vào tính năng riêng của một host cụ thể** (một API subagent riêng, một loại hook, một tên công cụ đặc thù).

**Bằng chứng còn thiếu.** Không có; đây là quyết định về phạm vi (scope).

---

## Q13 — Liệu harness có nên bắt buộc tuân thủ TDD, hay chỉ yêu cầu bằng chứng và cho phép thứ tự linh hoạt? **P1**

**Tại sao quan trọng.** Superpowers biến chu trình red-green-refactor thành luật thép; Spec Kit biến test thành tùy chọn; GSD biến TDD thành một chế độ bạn tự chọn tham gia theo từng plan. Không có bằng chứng nào trong tài liệu tham chiếu cho thấy việc tuân thủ nghiêm ngặt TDD giúp cải thiện đầu ra của agent — chỉ có bằng chứng cho thấy *test đóng vai trò bằng chứng* làm được điều đó. Việc bắt buộc thứ tự can thiệp sâu hơn nhiều so với việc bắt buộc bằng chứng, và những quy tắc can thiệp sâu nhưng khó xác minh chính là những quy tắc dễ bị làm giả nhất.

**Các phương án.**

- **A. TDD nghiêm ngặt, có kiểm chứng.** Quỹ đạo (trajectory) của mỗi task bắt buộc phải cho thấy một lần chạy thất bại (đỏ) trước một lần chạy thành công (xanh). Mạnh mẽ, và có thể kiểm tra cơ học từ trajectory.
- **B. Chỉ cần bằng chứng (Evidence-only).** Yêu cầu một test giải tỏa được yêu cầu và chạy pass; không quan tâm nó được viết khi nào.
- **C. Điều kiện hóa theo loại tác vụ (Kind-conditional).** Nghiêm ngặt đối với các task được gắn thẻ claim `INV-` hoặc một bản tái hiện bug (nơi mà câu hỏi "liệu bài test có thực sự kiểm tra đúng vấn đề hay không" là toàn bộ câu hỏi); chỉ cần bằng chứng ở những nơi khác.

**Khuyến nghị. C.** Nó đặt kỷ luật đắt đỏ vào chính xác nơi mà dạng thất bại nó ngăn chặn là có thật: một bài test được viết sau khi đã sửa xong, dựa trên đoạn code đã sửa, thường xuyên pass vì lý do sai lệch. Đối với các tác vụ tính năng thông thường, bằng chứng là đủ, và việc kiểm tra trajectory vẫn ghi nhận lại những gì đã xảy ra.

**Bằng chứng còn thiếu.** Liệu TDD nghiêm ngặt có làm thay đổi tỷ lệ lỗi đối với code do agent viết hay không. Chưa ai trong tài liệu tham chiếu từng đo lường điều này; `forge stats` (Q1) có thể làm được.

---

## Q14 — Liệu một bootstrap mặc-định-từ-chối có quá mỏng để trở nên hữu ích? **P1**

**Tại sao quan trọng.** WORKFLOW.md §5 đề xuất giới hạn tối đa 40 claim, một tư thế mặc-định-từ-chối (reject-by-default), và gọi một baseline gồm 12 claim được phê chuẩn là một kết quả tốt. Điều đó có thể khiến kho lưu trữ quá thưa thớt đến mức quy tắc chạm-claim hầu như không bao giờ được kích hoạt và giá trị của harness trở nên vô hình trong tháng đầu tiên — đúng vào thời điểm quyết định việc tiếp tục sử dụng hay từ bỏ.

**Các phương án.**

- **A. Mặc định từ chối, trần tối đa 40** (được đề xuất).
- **B. Baseline hào phóng** với mọi thứ được đánh dấu là `asserted` và có độ tin cậy `confidence`, dựa vào các linter để bắt nhiễu. Mang lại cảm giác giá trị nhanh hơn, rủi ro cao hơn về việc một kho lưu trữ đầy rẫy các claim nghe có vẻ hợp lý nhưng lại sai lệch — vốn là dạng thất bại mà toàn bộ thiết kế này sinh ra để ngăn chặn.
- **C. Mặc định từ chối, nhưng tập trung ưu tiên trước hai loại có giá trị cao nhất**: phỏng vấn để lấy `CON-` (từ vựng/khái niệm) và `PIT-` (các cạm bẫy đã biết) thay vì quét tìm `CMP-`/`ARC-`. Hai loại này là không thể phái sinh từ code, chi phí xác nhận rẻ, và ngay lập tức hữu ích cho một agent.
- **D. Hoàn toàn không tạo claim nào khi bootstrap.** Chỉ tạo tầng phái sinh; các claim sẽ tích lũy dần từ những thay đổi đầu tiên.

**Khuyến nghị. C.** Một kho lưu trữ gồm 8 khái niệm và 6 cạm bẫy, tất cả đều được con người xác nhận, sẽ hữu ích hơn nhiều trong ngày đầu tiên so với 40 mô tả component được suy diễn tự động, và nó làm cho phase `investigate` đầu tiên trở nên tốt hơn rõ rệt. Giữ nguyên mức trần. Phương án D hấp dẫn vì sự thuần khiết nhưng lại đánh mất giá trị của tuần đầu tiên vốn mang tính quyết định việc gắn bó với công cụ.

**Bằng chứng còn thiếu.** Những loại claim nào thực sự được trích dẫn trong các phase điều tra thực tế. Gắn thiết bị đo lường việc sử dụng `forge trace` để tìm câu trả lời.

---

## Q15 — Làm thế nào để tỷ lệ `enforced` không biến thành một chỉ số bị thao túng (game the metric)? **P2**

**Tại sao quan trọng.** `forge status` báo cáo tỷ lệ `enforced` so với `asserted` theo từng loại, và CONSTITUTION.md V coi `asserted` là một trạng thái trung thực. Nhưng bất kỳ tỷ lệ nào được báo cáo cũng mời gọi sự thao túng — ở đây, bằng cách gắn một bài test yếu ớt hoặc một quy tắc dễ dàng thỏa mãn vào một claim chỉ để dán nhãn nó là `enforced`.

**Các phương án.**

- **A. Báo cáo và tin tưởng.** Harness cá nhân, một lập trình viên duy nhất, không có động cơ để tự lừa dối mình.
- **B. Yêu cầu bằng chứng phải từng được quan sát thấy thất bại ít nhất một lần** — một quy tắc chưa từng thất bại có thể chẳng ràng buộc được bất cứ điều gì. Về mặt cơ học: ghi nhận lần thất bại đầu tiên được quan sát của mỗi artifact bằng chứng.
- **C. Không đưa ra tỷ lệ.** Chỉ báo cáo số lượng tuyệt đối các claim chưa được enforced thuộc các loại có giá trị cao.

**Khuyến nghị. A cho MVP, B nếu vấn đề này trở nên đáng lo ngại.** B thực sự thanh nhã — đó là nguyên tắc "nếu bạn chưa từng chứng kiến bài test fail, bạn không thể biết nó có kiểm tra đúng thứ hay không" của Superpowers áp dụng cho bằng chứng của claim — nhưng nó cần một nơi để ghi nhận lần-thất-bại-được-quan-sát-đầu-tiên, vốn là trạng thái (state), thứ mà thiết kế luôn muốn né tránh. Xem xét lại nếu tỷ lệ này bắt đầu trông tốt một cách đáng ngờ.

**Bằng chứng còn thiếu.** Không có; đây là một nhận định về các động cơ khuyến khích mà chỉ có quá trình sử dụng thực tế mới giải quyết được.
