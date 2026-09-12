# ARCHITECTURE.md — Kiến trúc Hệ thống Forge

Kiến trúc nội tại của harness **Forge**. 

Tài liệu này xác định ranh giới kỹ thuật: đây là loại hệ thống gì, các thành phần cấu thành, mô hình dữ liệu và trạng thái, bề mặt lệnh CLI, và các quy tắc kiến trúc chi phối toàn bộ hệ thống.

---

## 1. Đây là loại hệ thống gì?

**Forge là một framework kỹ nghệ phần mềm cục bộ bên trong repository, được cấu thành từ ba tầng: một Kernel CLI mang tính xác định (deterministic), một tập hợp các Skills hướng dẫn cho AI, và các Artifact văn bản thuần lưu trực tiếp trong Git. Forge không phải là một AI Agent, không phải một bộ điều phối (orchestrator), và không phải là một nền tảng server cồng kềnh.**

### Phân tích định vị hệ thống:

| Hình thái ứng viên | Nhận định & Quyết định |
|---|---|
| **Chỉ là một tập hợp các Skill / Prompt** | **Đứng riêng lẻ là không đủ.** Việc kiểm soát AI chỉ dựa trên prompt buộc phải dùng câu từ gắt gao ("bạn không có sự lựa chọn"), nhưng AI vẫn có thể lờ đi hoặc giải thích bao biện khi ngữ cảnh dài. Prompt không thể tính toán toán học tập hợp claim bị chạm, không thể diff mã băm cây cú pháp (AST). |
| **Chỉ là một CLI đơn thuần** | **Cần thiết nhưng chưa đủ.** CLI thuần túy là công cụ cơ học; nó không thể tự hiểu ngữ cảnh nghiệp vụ hay tự soạn thảo một bản đặc tả logic. |
| **Một Agent Orchestration riêng biệt** | **Từ chối.** Các Host Agent hiện đại (Claude Code, Cursor, Copilot CLI, Antigravity,...) đã sở hữu vòng lặp thực thi hoàn chỉnh, quản lý công cụ shell/file và mô hình LLM. Xây dựng một agent cạnh tranh với các công cụ này là lãng phí tài nguyên và không tạo ra đòn bẩy. |
| **Framework cục bộ (Local Framework)** | **Quyết định đúng đắn nhất.** Đóng vai trò là container tích hợp: tận dụng năng lực của Host Agent, hướng dẫn bằng Skills, và giám sát cơ học bằng Kernel CLI. |

```
┌─────────────────────────────────────────────────────────────────────────┐
│  HOST AGENT  (Claude Code / Cursor / Copilot CLI / Antigravity / …)     │
│  Nắm giữ: vòng lặp thực thi, công cụ tệp & shell, subagents, mô hình LLM│
│  Forge không thay thế, không bọc ngoài, không làm lại phần này          │
└───────────────┬──────────────────────────────────────┬──────────────────┘
                │ gọi skills                           │ chạy lệnh CLI
                ▼                                      ▼
┌───────────────────────────────┐      ┌───────────────────────────────────┐
│  SKILLS  (Tầng Phán đoán)     │      │  KERNEL  `forge`  (Tầng Cơ chế)   │
│  Quy trình Markdown, kích hoạt│◄────►│  Xác định (Deterministic).        │
│  theo nhu cầu. Soạn thảo text.│ JSON │  TUYỆT ĐỐI KHÔNG gọi LLM.         │
│  Không có quyền tự cưỡng chế. │      │  Mã thoát lệnh (Exit code) là Gate│
└───────────────┬───────────────┘      └───────────────┬───────────────────┘
                │                                      │
                └──────────────┬───────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  ARTIFACTS  (Tầng Trạng thái) — Văn bản thuần (Plain-text) trong Git   │
│  docs/system/**   changes/**   .forge/**                                │
│  Git là database duy nhất. Tuyệt đối không có cơ sở dữ liệu ngầm khác.  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Ba quy tắc bất khả xâm phạm
1. **Kernel không bao giờ gọi mô hình LLM:** Mọi kết quả từ Kernel CLI đều có tính tái lập tuyệt đối 100% từ commit của repository. Đây là nền tảng để các cổng kiểm soát (gates) trở nên hoàn toàn khách quan và đáng tin cậy.
2. **Các Skill không bao giờ tự thực thi cưỡng chế:** Một skill có thể khuyên dừng lại, nhưng *phép kiểm tra* biện minh cho sự dừng lại đó bắt buộc phải là một lệnh của Kernel CLI. Nếu một quy tắc là quan trọng, nó phải được thể hiện bằng một mã thoát (exit code); nếu không thể là mã thoát, nó chỉ là chỉ dẫn định hướng.
3. **Mọi trạng thái đều là văn bản trong Git:** Không dùng database, không daemon chạy ngầm, không cache ngầm gây bất đồng pha với repository. Dữ liệu phái sinh (derived tier) được commit và có thể tái tạo lại hoàn toàn đồng nhất từng byte.

---

## 2. Các thành phần chính

### 2.1 Kernel (`forge`) — Sáu module cốt lõi

| Module | Trách nhiệm chính | Đầu vào | Đầu ra |
|---|---|---|---|
| **`store`** | Phân tích, xác thực và chỉnh sửa kho lưu trữ claim cùng các ADR | `docs/system/**` | Các claim có kiểu, các issue kiểm định |
| **`graph`** | Nạp DAG artifact, giải quyết thứ tự phụ thuộc, phái sinh trạng thái hoàn thành, giải quyết hợp đồng ngữ cảnh | `.forge/schema/*.yaml`, filesystem | Artifact tiếp theo, tập hợp bị chặn, `instructions --json` |
| **`anchor`** | Phân giải neo, tính toán fingerprint AST đã chuẩn hóa, phân loại độ lỗi thời (fresh/stale/missing) | Claims, Git, Tree-Sitter | Trạng thái chi tiết cho từng neo |
| **`derive`** | Tạo tầng phái sinh bằng cách gọi ra các công cụ phân tích code sẵn có | Repo, `.forge/config.yaml` | `derived/*.json` |
| **`gate`** | Chạy các kiểm tra đã đăng ký tại từng điểm vòng đời; tổng hợp mức độ nghiêm trọng; trả về exit code | `.forge/config.yaml`, các module khác | Pass/Fail + danh sách phát hiện (findings) |
| **`trace`** | Quét các claim, ADR, change, test và các tham chiếu ngược trong code; xây dựng chỉ mục truy vết 2 chiều | Toàn bộ codebase | `derived/trace.json` |

*Chủ ý không xây dựng: client gọi mô hình AI, registry công cụ riêng, sandbox, server, plugin loader.*

### 2.2 Bề mặt lệnh (Command Surface)
Toàn bộ bề mặt lệnh được thiết kế nhỏ gọn (~20 lệnh), hỗ trợ `--json` và trả về mã thoát chuẩn xác (0: thành công, 1: có phát hiện/lệch, 2: lỗi cú pháp):

```bash
# Quản trị & Trạng thái
forge init                              # Khởi tạo khung cấu trúc .forge/ và docs/system/
forge doctor                            # Kiểm tra môi trường công cụ (python, git, grammars, test)
forge status                            # Báo cáo tổng quan 1 màn hình: track, phase, claims, drift, tests
forge check [--scope store|change|all]  # Chạy toàn bộ các bài kiểm định xác định

# Cổng kiểm soát & Đồng bộ
forge gate <point> [--change N]         # Chạy các cổng kiểm soát tại điểm vòng đời
forge sync derived                      # Tái tạo lại tầng phái sinh
forge verify --change <N>               # Chạy kiểm chứng toàn diện, sinh verification.json

# Quản lý Trôi dạt Tri thức (Drift)
forge drift [--store|--changed] [--json]# Kiểm tra độ lỗi thời của anchor theo AST
forge drift record                      # Mở các mục mới trong sổ cái DRIFT.md
forge drift resolve <D-id> --verdict V  # Ghi nhận phán quyết xử lý độ lệch
forge drift waive <D-id> --reason TEXT  # Tạm hoãn độ lệch kèm lý do

# Quản lý Claim tri thức
forge claim new <kind> [--append]       # Tạo claim mẫu (invariant, concept, architecture,...)
forge claim show <ID>                   # Hiển thị chi tiết một claim
forge ratify <ID>                       # Phê chuẩn candidate claim thành chính thức
forge retire <ID> --ground <1-4>        # Thu hồi claim theo 1 trong 4 căn cứ hợp lệ
forge trace <ID> [--json]               # Truy vết 2 chiều một mã Claim

# Vòng đời Thay đổi (Change Lifecycle)
forge change new <slug> --track A|B|C   # Khởi tạo thay đổi mới
forge change show <N>                   # Xem tiến độ và các artifact còn thiếu
forge change track <N> --to C --reason  # Nâng cấp track (bánh cóc một chiều)
forge instructions <artifact> --change N# Cung cấp hợp đồng ngữ cảnh cho AI
forge impact --change <N>               # Tính toán bán kính ảnh hưởng & claim bị chạm
forge archive --change <N>              # Gập delta spec vào hệ thống chính và lưu trữ
```

### 2.3 Các Skills (Tầng tư duy cho AI)
Hệ thống gồm 7 skill cốt lõi, mỗi skill là một file `SKILL.md` tuân thủ ngân sách tối đa 250 dòng:

| Skill | Phase | Nhiệm vụ |
|---|---|---|
| `forge` (router) | understand | Phân loại track (A/B/C), phát biểu lại ý định của người dùng, mở change |
| `investigate` | investigate | Đọc code hiện hữu trước khi sửa; đề xuất candidate claim kèm độ tin cậy |
| `specify` | spec | Chuyển ý định thành các yêu cầu delta và các kịch bản kiểm thử |
| `assess-impact` | impact | Rà soát bán kính ảnh hưởng cơ học và các vùng ảnh hưởng tĩnh |
| `plan-tasks` | tasks | Phân rã spec thành các task kiểm thử độc lập, mỗi task gắn mã `REQ-` |
| `implement` | implement | Thực thi từng task theo chu trình TDD (Red ➔ Green ➔ Refactor) |
| `curate-knowledge` | sync | Cập nhật tri thức đã học được vào kho lưu trữ, xử lý sổ cái drift |
| `bootstrap` | bootstrap | Khảo sát toàn bộ repository từ đầu để xây dựng kho tri thức tin cậy |

---

## 3. Bố cục thư mục chuẩn trong Repository

```
.
├── .forge/
│   ├── config.yaml            # Tệp cấu hình dự án duy nhất
│   ├── schema/                # Khai báo đồ thị DAG artifact cho các loại thay đổi
│   │   ├── feature.yaml
│   │   ├── bugfix.yaml
│   │   └── refactor.yaml
│   └── templates/             # Các mẫu văn bản chuẩn (spec.md, impact.md, tasks.md,...)
│
├── docs/system/               # KHO TRI THỨC VĨNH VIỄN
│   ├── OVERVIEW.md            # Bức tranh kiến trúc tổng quan (luôn được nạp)
│   ├── DRIFT.md               # Sổ cái ghi nhận và xử lý độ lệch tri thức
│   ├── domain.md              # Các quy tắc domain & Invariants
│   ├── decisions/             # Các quyết định kiến trúc (ADR-0001, ADR-0002,...)
│   └── derived/               # TẦNG PHÁI SINH (sinh tự động từ code, commit vào Git)
│       ├── trace.json         # Chỉ mục truy vết 2 chiều
│       ├── deps.json          # Đồ thị phụ thuộc module
│       └── inventory.json     # Danh mục symbol/endpoint
│
├── changes/                   # CÁC THAY ĐỔI ĐANG THỰC HIỆN
│   ├── 0001-refund-support/
│   │   ├── .forge.yaml        # Track, siêu dữ liệu của change
│   │   ├── proposal.md        # Bản đề xuất thay đổi
│   │   ├── spec/              # Đặc tả delta
│   │   ├── impact.md          # Giải trình theo quy tắc claim-touch
│   │   ├── tasks.md           # Danh sách nhiệm vụ TDD
│   │   └── verification.json  # Bằng chứng nghiệm thu cơ học
│   └── archive/               # Kho lưu trữ các change đã đóng (chỉ-đọc)
│
└── src/ & tests/              # Mã nguồn và bài kiểm thử của dự án
```

---

## 4. Các Mô hình Cốt lõi (Core Models)

### 4.1 Mô hình Đồ thị Artifact (Artifact DAG)
Một artifact là một node trong đồ thị phụ thuộc (DAG). Trạng thái hoàn thành được phái sinh trực tiếp từ sự tồn tại của tệp trên filesystem:

```yaml
name: feature
version: 1
tracks: [B, C]
artifacts:
  - id: proposal
    generates: proposal.md
    requires: []
    tracks: [B, C]
  - id: spec
    generates: "spec/**/*.md"
    requires: [proposal]
    tracks: [B, C]
    reads:                             # Hợp đồng ngữ cảnh tối thiểu
      - changes/${change}/proposal.md
      - docs/system/domain.md
  - id: impact
    generates: impact.md
    requires: [spec]
    tracks: [C]
    reads:
      - changes/${change}/spec/**
      - derived: [deps, inventory]
      - claims: metadata
  - id: tasks
    generates: tasks.md
    requires: [spec, impact]
    tracks: [B, C]
```

### 4.2 Mô hình Trạng thái (Zero State Files)
Forge **không có tệp trạng thái riêng**. Mọi câu hỏi về trạng thái đều được tính toán động từ filesystem và Git:

| Câu hỏi về trạng thái | Cơ chế tính toán |
|---|---|
| Artifact nào đã hoàn thành? | Tệp tương ứng tại `generates` đã tồn tại trên đĩa |
| Bước nào đang bị chặn? | Danh sách `requires` trong DAG trừ đi các artifact đã tồn tại |
| Track hiện tại là gì? | Đọc từ `changes/NNNN/.forge.yaml` |
| Task nào đã hoàn thành? | Quét các ô tích `- [x]` trong `tasks.md` |
| Tri thức có bị lỗi thời không? | So khớp AST fingerprint của anchor so với commit SHA được ghi nhận |
| Có vấn đề nào tồn đọng chưa xử lý? | Quét các mục chưa có phán quyết trong `DRIFT.md` |

**Lợi ích lớn:** Không bao giờ xảy ra tình trạng lệch pha trạng thái; lệnh `git checkout` một commit cũ sẽ tái hiện chính xác 100% trạng thái của Forge tại thời điểm commit đó mà không cần bất kỳ thao tác đồng bộ nào.

### 4.3 Mô hình Kiểm định 3 Tầng (Validation Model)
Mọi vấn đề kiểm định đều thuộc 1 trong 3 tầng trách nhiệm:

```
┌────────────────────────────────────────────────────────────────────────┐
│ 1. TẦNG CẤU TRÚC (STRUCTURAL) - Parser của Kernel                      │
│    Cú pháp claim block, format ID duy nhất, cấu trúc DAG                │
│    ➔ KẾT QUẢ: ERROR (Chặn cổng Gate ngay lập tức)                      │
├────────────────────────────────────────────────────────────────────────┤
│ 2. TẦNG QUAN HỆ (RELATIONAL) - Kernel + trace.json                     │
│    Độ phủ Requirement ↔ Task ↔ Test, tính trọn vẹn của Claim-Touch     │
│    ➔ KẾT QUẢ: ERROR (Chặn cổng Gate ngay lập tức)                      │
├────────────────────────────────────────────────────────────────────────┤
│ 3. TẦNG NGỮ NGHĨA (SEMANTIC) - AI Agent qua Skill                      │
│    Logic này có hợp lý không? Đặt tên hàm có nhất quán không?          │
│    ➔ KẾT QUẢ: FINDING (Mang tính tư vấn, con người có quyền phủ quyết) │
└────────────────────────────────────────────────────────────────────────┘
```
**Nguyên tắc thiết kế:** Bất cứ kiểm tra nào có thể chuyển từ tầng Ngữ nghĩa xuống tầng Quan hệ hoặc Cấu trúc (bằng cách đặt mã ID hoặc định nghĩa trường dữ liệu) đều bắt buộc phải chuyển xuống.

---

## 5. Các Lựa chọn Kỹ thuật Nền tảng

1. **Ngôn ngữ: Python >= 3.11 (Ưu tiên thư viện chuẩn):**
   - Chạy độc lập trên bất kỳ codebase nào (JavaScript, Go, Rust, Python, Java...).
   - `pathlib` được sử dụng toàn diện để tương thích tuyệt đối giữa Windows, macOS và Linux.
2. **Ngân sách Dependency tối giản:**
   - Chỉ sử dụng 2 thư viện bên ngoài cốt lõi: `tree-sitter` (phân tích AST) và `pyyaml` (đọc file cấu hình).
   - Mọi thao tác khác đều sử dụng `subprocess` gọi các công cụ sẵn có của hệ thống (Git, test runners).
3. **An toàn bảo mật:**
   - Mọi tham số truyền vào Git đều được bọc mảng đối số tường minh, tuyệt đối không dùng shell string để ngăn chặn nguy cơ command injection.
