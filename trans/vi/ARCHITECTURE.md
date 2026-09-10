# ARCHITECTURE.md — Kiến trúc hệ thống

Kiến trúc của chính harness. Tên làm việc: **forge**.

Đọc tiếp từ [SYSTEM_KNOWLEDGE.md](SYSTEM_KNOWLEDGE.md) (những gì được lưu trữ) và [WORKFLOW.md](WORKFLOW.md) (những gì diễn ra). Tài liệu này giải đáp mục §6 của bản tóm lược nhiệm vụ: đây là loại hệ thống gì, cái gì nằm ở đâu, và nó được kiểm định như thế nào.

---

## 1. Đây là loại hệ thống gì?

**Câu trả lời: một framework cục bộ trong repository được cấu thành từ ba tầng — một kernel CLI mang tính xác định, một tập hợp nhỏ các skill LLM, và các artifact văn bản thuần lưu trong git. Nó không phải là một agent, không phải bộ điều phối (orchestrator), và không phải là một nền tảng (platform).**

Bản tóm lược nhiệm vụ đưa ra năm hình thái ứng viên. Đánh giá cụ thể:

| Ứng viên | Nhận định |
|---|---|
| Một tập hợp các skill | **Đứng riêng lẻ là không đủ.** Superpowers chứng minh rằng các skill có thể thay đổi hành vi, nhưng cũng chứng minh rằng việc thực thi chỉ dựa trên prompt buộc phải "gào thét" mới giữ được kỷ luật. Các skill không thể tính toán tập hợp chạm-claim hay so sánh diff dấu vân tay AST |
| Một CLI | **Cần thiết nhưng chưa đủ.** Một CLI không thể tự viết spec hay phán đoán một bản thiết kế |
| Một prompt/skill framework | Tương tự phương án (1) |
| Một tầng điều phối agent | **Bị từ chối.** Agent của host (Claude Code, Codex, Copilot CLI, …) đã nắm giữ vòng lặp thực thi, sở hữu các công cụ và quản lý các subagent. mini-SWE-agent cho thấy một vòng lặp ~200 dòng là đủ sức cạnh tranh; việc viết một bộ điều phối tốt hơn không phải là nơi tạo ra đòn bẩy |
| Một framework cục bộ trong repository | **Chính xác — đóng vai trò là vỏ bọc chứa các mảnh ghép còn lại** |

Do đó: **CLI + skills + artifacts, kèm theo một quy tắc thép phân định rõ tầng nào sở hữu cái gì.**

```
┌─────────────────────────────────────────────────────────────────────────┐
│  HOST AGENT  (Claude Code / Codex / Copilot CLI / …)                    │
│  Nắm giữ: vòng lặp thực thi, công cụ tệp & shell, subagents, model      │
│  forge không thay thế, không bọc ngoài, không triển khai lại phần này    │
└───────────────┬──────────────────────────────────────┬──────────────────┘
                │ gọi skills                           │ chạy lệnh
                ▼                                      ▼
┌───────────────────────────────┐      ┌───────────────────────────────────┐
│  SKILLS  (phán đoán)          │      │  KERNEL  `forge`  (cơ chế)        │
│  Quy trình markdown, kích hoạt│◄────►│  Xác định. TUYỆT ĐỐI KHÔNG gọi    │
│  theo nhu cầu. Viết artifacts.│ JSON │  LLM. Mã thoát lệnh là các cổng.  │
│  Không thể tự thực thi gì.    │      │  Chỉ đọc/ghi văn bản thuần + git. │
└───────────────┬───────────────┘      └───────────────┬───────────────────┘
                │                                      │
                └──────────────┬───────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  ARTIFACTS  (trạng thái) — văn bản thuần, lưu trong git                 │
│  docs/system/**   changes/**   .forge/**                                │
│  Git là database. Tuyệt đối không có kho lưu trạng thái nào khác.       │
└─────────────────────────────────────────────────────────────────────────┘
```

### Ba quy tắc bất khả xâm phạm

1. **Kernel không bao giờ gọi mô hình LLM.** Mọi đầu ra của kernel đều có thể tái tạo lại được từ repository tại một commit nhất định. Đây chính là yếu tố làm cho các cổng kiểm soát (gates) trở nên đáng tin cậy.
2. **Các skill không bao giờ tự thực thi cưỡng chế.** Một skill có thể từ chối đi tiếp, nhưng *phép kiểm tra* biện minh cho sự từ chối đó phải là một lệnh của kernel. Nếu một quy tắc là quan trọng, nó phải là một mã thoát (exit code); nếu nó không thể là một mã thoát, nó là một chỉ dẫn định hướng và được viết như một chỉ dẫn.
3. **Mọi trạng thái đều là văn bản trong git.** Không có database, không có tiến trình daemon, không có bộ nhớ cache nào có thể bất đồng với repository. Dữ liệu phái sinh được commit và có thể tái tạo lại được; việc phái sinh hai lần tại cùng một commit phải tạo ra các byte đồng nhất tuyệt đối.

---

## 2. Các thành phần

### 2.1 Kernel (`forge`) — sáu module

| Module | Trách nhiệm | Đầu vào chính | Đầu ra chính |
|---|---|---|---|
| **`store`** | Phân tích, xác thực và chỉnh sửa kho lưu trữ claim cùng các ADR | `docs/system/**` | các claim có kiểu, các issue kiểm định |
| **`graph`** | Nạp DAG artifact, giải quyết thứ tự, phái sinh trạng thái hoàn thành, giải quyết hợp đồng ngữ cảnh | `.forge/schema/*.yaml`, hệ thống tệp | artifact tiếp theo, tập hợp bị chặn, `instructions --json` |
| **`anchor`** | Phân giải các neo, tính toán fingerprint AST đã chuẩn hóa, phân loại độ lỗi thời | claims, git, tree-sitter | `fresh`/`stale`/`missing`/`coarse` cho từng neo |
| **`derive`** | Tạo tầng phái sinh bằng cách gọi ra các công cụ của hệ sinh thái | repo, `.forge/config.yaml` | `derived/*.json` |
| **`gate`** | Chạy các kiểm tra đã đăng ký tại một điểm vòng đời; tổng hợp mức độ nghiêm trọng; trả về mã thoát | `.forge/config.yaml`, các module khác | pass/fail + các phát hiện (findings) |
| **`trace`** | Quét các claim, ADR, change, test và các tham chiếu ngược trong code; xây dựng chỉ mục | tất cả mọi thứ | `derived/trace.json` |

Chủ ý **không** xây dựng các module: client gọi mô hình, registry công cụ, sandbox, scheduler, server, plugin loader.

### 2.2 Bề mặt lệnh (Command surface)

Được tinh giản có chủ đích. Mọi lệnh đều có thể viết script tự động, hỗ trợ cờ `--json`, và trả về mã thoát khác 0 khi thất bại.

```
forge init                              # khởi tạo khung cấu trúc .forge/ và docs/system/
forge status                            # xem trên 1 màn hình: track, phase, tập bị chặn, drift, nợ kỹ thuật, ngân sách, tỷ lệ enforced/asserted

forge check [--scope store|change|all]  # chạy toàn bộ các kiểm định xác định (§5)
forge gate <point> [--change N]         # chạy các cổng được đăng ký tại một điểm vòng đời

forge sync derived [--paths ...]        # tạo lại tầng phái sinh
forge sync change <N>                   # gập lưu trữ (archive fold) + neo lại (re-anchor) (WORKFLOW §3.10)

forge drift [--paths ...] [--json]      # kiểm tra độ lỗi thời neo + tuân thủ quy tắc + khoảng trống cấu trúc
forge drift resolve <D-id> --verdict V1|V2|V3|V4 [--adr N] [--evidence TEXT]
forge drift waive <D-id> --reason TEXT --until <sha|date>

forge claim new <kind> | show <ID> | edit <ID>
forge ratify <ID>                       # chuyển từ ứng viên (candidate) -> đã phê chuẩn (ratified)
forge retire <ID> --ground 1|2|3|4 --evidence TEXT
forge reanchor <ID>                     # chỉ thực hiện khi fingerprint không đổi theo ánh xạ đổi tên

forge impact --change <N>               # bán kính ảnh hưởng ứng viên + tập hợp chạm-claim được tính toán
forge trace <ID> [--json]               # hai chiều: những gì tham chiếu đến mục này, và mục này tham chiếu đến đâu
forge verify --change <N>               # tạo ra verification.json

forge change new <slug> --track A|B|C
forge change track <N> --upgrade B|C --reason TEXT
forge archive <N>

forge instructions <artifact> --change <N> --json   # hợp đồng ngữ cảnh + chỉ dẫn cho một phase
forge adr new <slug>
forge bootstrap derive | review | seal
```

Khoảng 20 lệnh. Để so sánh, GSD Core có tới ~68 slash command và 44 gói capability.

### 2.3 Các Skill

Chín skill, và số lượng này nằm trong ngân sách cố định (xem [CONSTITUTION.md](CONSTITUTION.md)). Mỗi skill là một tệp `SKILL.md`, mỗi tệp dưới ~250 dòng, mỗi tệp đều có các bài kiểm thử áp lực (pressure tests).

| Skill | Phase | Làm điều gì mà kernel không thể làm |
|---|---|---|
| `forge` (router) | entry | Phân loại track, phát biểu lại ý định, định tuyến. Chỉ đọc, từ chối đoán mò |
| `investigate` | investigate | Đọc code và quyết định điều gì đáng để biết; đưa ra các ứng viên kèm độ tin cậy |
| `specify` | spec | Chuyển ý định thành các yêu cầu delta và các kịch bản kiểm thử |
| `assess-impact` | impact | Tuyển chọn bán kính ảnh hưởng đã tính toán; tìm các consumer mà phân tích tĩnh không thấy |
| `design` | design | Chọn một phương án tiếp cận, nêu các phương án thay thế, viết ADR |
| `plan-tasks` | tasks | Phân rã thành các đơn vị có thể review và kiểm thử được với interface thực tế |
| `implement` | implement | Thực thi một task, theo TDD, bên trong phạm vi tệp được phép |
| `review` | implement / verify | Review 2 giai đoạn: tuân thủ spec, sau đó đến chất lượng code |
| `curate-knowledge` | sync / drift | Đề xuất chỉnh sửa claim, các dòng ghi sổ cái, và các phán quyết về độ lệch |

Chủ ý vắng mặt: các nhân cách (chuyên viên phân tích, PM, kiến trúc sư, UX), trình tạo skill, brainstorming dưới dạng một skill riêng biệt (đó là việc của router), chế độ party mode, hồi tưởng (retrospectives), PRD/PRFAQ.

### 2.4 Những gì host agent cung cấp và chúng ta không được phép xây dựng lại

Đọc/ghi/sửa tệp; shell; tìm kiếm (grep/glob); tạo subagent; mô hình LLM; nén ngữ cảnh phiên làm việc; tích hợp git; các lời nhắc cấp quyền. Mỗi mục trong số này đều là nơi một harness có thể mọc thêm một bản triển khai cạnh tranh, và mỗi bản triển khai đó chắc chắn sẽ tệ hơn bản của host.

---

## 3. Cấu trúc thư mục Repository

### 3.1 Thư mục riêng của harness

```
.forge/
  config.yaml            # tệp cấu hình duy nhất
  constitution.md        # các nguyên tắc kỹ nghệ (do con người sửa đổi; xem CONSTITUTION.md)
  schema/
    feature.yaml         # DAG artifact: workflow thay đổi mặc định
    bugfix.yaml
    refactor.yaml
    architecture.yaml
    knowledge.yaml
  templates/
    proposal.md  spec.md  impact.md  design.md  tasks.md  adr.md  claim.md
  rules/                 # cấu hình tuân thủ của hệ sinh thái, gắn thẻ ngược lại các claim
    deps.cjs             # hoặc các bài test archunit / tach.toml / deptrac.yaml
  checks/                # các script kiểm tra riêng của dự án được bằng chứng của claim tham chiếu đến
  skills/                # chín tệp SKILL.md (hoặc một plugin của host trỏ vào đây)
  cache/                 # được đưa vào gitignore. Chỉ chứa fingerprint. Xóa thư mục này không đổi gì ngoài tốc độ
```

**Những thứ bị từ chối từ cấu trúc phác thảo ban đầu:**

- `rules/` dưới dạng các quy tắc *văn xuôi* — bản phác thảo ban đầu gợi ý một thư mục chứa các tài liệu quy tắc bằng văn xuôi. Quy tắc văn xuôi thuộc về `constitution.md` (quản trị) hoặc dưới dạng các claim (đặc thù cho hệ thống). Thư mục `.forge/rules/` ở đây nắm giữ các cấu hình tuân thủ *có thể thực thi được*. Việc có cả thư mục `rules/` văn xuôi lẫn tệp `constitution.md` chắc chắn sẽ dẫn đến việc chúng bị phân kỳ bất đồng bộ.
- `workflows/` dưới dạng một thư mục chứa các tài liệu quy trình — GSD có ~90 tệp loại này và đó là triệu chứng rõ ràng nhất của việc xây dựng thừa thãi. Workflows là các khai báo DAG trong `schema/`; quy trình thực hiện là các skill.
- `config/` dưới dạng một thư mục — chỉ có một tệp `config.yaml` duy nhất. Một thư mục cấu hình là nơi cấu hình bắt đầu bị chia cắt manh mún.
- Một thư mục `state/` — trạng thái được phái sinh từ hệ thống tệp (cơ chế của OpenSpec). Thứ duy nhất nằm dưới `.forge/` không phải là mã nguồn là `cache/`, và nó được chủ ý thiết kế để có thể xóa bỏ bất cứ lúc nào.

### 3.2 Các thư mục Tri thức và Thay đổi (Knowledge and change directories)

```
docs/system/            # tri thức vĩnh viễn — xem SYSTEM_KNOWLEDGE.md §2.1
changes/
  0004-refund-support/
    .forge.yaml         # track, thời điểm tạo, nâng cấp từ đâu, skip_spec + lý do
    proposal.md         # (track B: bao gồm phần `## Claims touched`)
    investigation.md    # track C
    spec/<capability-path>/spec.md
    impact.md           # track C
    design.md           # track C, hoặc khi bắt buộc phải có ADR
    tasks.md
    analysis.md         # được sinh bởi lệnh `analyze`
    verification.json   # được sinh bởi lệnh `verify`
    trajectories/*.json # bản ghi thực thi theo từng task
  archive/
    2026-09-10-0003-idempotent-capture/
```

**Quy ước đặt tên.** `changes/NNNN-<slug>/`, có đệm số 0, tăng dần đơn điệu. `specs/` *không* được dùng cho các change — từ `spec` được dành riêng cho tầng vĩnh viễn để cụm từ "the spec" không bao giờ bị mơ hồ. Đây là đính chính trực tiếp đối với cấu trúc `specs/NNN-feature/` của Spec Kit, nơi mà thư mục theo từng tính năng lại chiếm mất cái tên vốn dĩ thuộc về bản mô tả bền vững của toàn hệ thống.

**Những thứ bị từ chối từ phác thảo change ban đầu:** `tests.md` (test là code; các kịch bản của spec đã mang theo ý định), `verification.md` (được sinh tự động, việc viết tay nó sẽ mời gọi các khẳng định chưa được kiểm chứng), `knowledge-sync.md` (đây là một thao tác lệnh, không phải tài liệu — phần khai báo nằm trong `impact.md` và phần thực thi nằm trong `forge sync`). Tối đa 5 artifact tự viết, 3 artifact cho một thay đổi có giới hạn (bounded change), và 1 artifact cho một thăm dò (probe).

### 3.3 `.forge/config.yaml`

Một tệp duy nhất, và nó là điểm tiếp giáp nơi dự án tùy biến mà không cần phải fork bất kỳ thứ gì.

```yaml
version: 1

commands:                       # cách build/test/lint cho CHÍNH dự án này
  build:     pnpm build
  typecheck: pnpm typecheck
  lint:      pnpm lint
  test:      pnpm test
  test_one:  pnpm test {file}
  test_list: pnpm test --reporter=json --listTests
  dep_rules: pnpm depcruise --config .forge/rules/deps.cjs
  contract:  pnpm openapi:generate -o {out}

derive:
  languages: [typescript, tsx]
  dep_tool: dependency-cruiser
  entry_globs: ["src/index.ts", "src/cli/*.ts"]

budgets:
  always_loaded_lines: 400      # không bao giờ nâng lên (xem CONSTITUTION.md)
  claims_max: 80                # mức trần mềm; vượt qua mức này, `forge status` yêu cầu review tỉa bớt
  bootstrap_claims_max: 40
  phase:
    investigate: { steps: 40, wall_seconds: 900 }
    task:        { steps: 30, wall_seconds: 600, max_consecutive_failures: 3 }

thresholds:
  structural_drift: 3
  review_debt_commits: 50
  derived_stale_commits: 20
  contract_severity: breaking   # mức nghiêm trọng oasdiff khiến cổng bị fail

autonomy:                       # WORKFLOW.md §4
  G3: always
  G5: always

rules:                          # được bơm vào quá trình sinh artifact (cơ chế của OpenSpec)
  spec:
    - Tiền tệ là số nguyên đơn vị nhỏ nhất (minor units); tuyệt đối không biểu diễn số tiền dưới dạng số thực (float) trong requirement
    - Mọi yêu cầu liên quan đến thanh toán đều phải nêu rõ hành vi tính lũy thừa (idempotency)
  design:
    - Ưu tiên một port hơn là một phụ thuộc trực tiếp khi liên quan đến tầng domain (xem ARC-3)
  tasks:
    - Một task migration luôn là [BLOCKING] và luôn đứng trước các task đọc cột mới

gates:                          # mô hình khai báo của GSD
  - point: investigate:pre
    check: derived.freshness
    blocking: false
    onError: skip
  - point: spec:post
    check: store.spec_grammar
    blocking: true
  - point: impact:post
    check: trace.claim_touch_complete
    blocking: true
  - point: analyze:post
    check: trace.requirement_task_coverage
    blocking: true
  - point: implement:pre
    check: derived.freshness
    blocking: true
  - point: implement:task:post
    check: task.scope_and_covers
    blocking: true
  - point: verify:post
    check: verify.definition_of_done
    blocking: true
  - point: verify:post
    check: drift.rules_conformance
    blocking: true
  - point: sync:pre
    check: store.valid
    blocking: true
  - point: converge:post
    check: repo.clean
    blocking: true
```

Tổng cộng 12 cổng, tại 10 điểm vòng đời. Riêng GSD đã có 14 cổng chỉ tại điểm `plan:pre`. Con số này là một ngân sách, không phải sự ngẫu nhiên: mọi cổng đều phải có thể biện minh trong một câu duy nhất, và các cổng không bao giờ kích hoạt sẽ bị xóa bỏ.

---

## 4. Các Mô hình (Models)

### 4.1 Mô hình Artifact

Một artifact là một tệp (hoặc glob) được khai báo dưới dạng một node trong DAG. Trực tiếp kế thừa thiết kế của OpenSpec, kèm hai sự bổ sung.

```yaml
name: feature
version: 1
tracks: [B, C]
artifacts:
  - id: proposal
    generates: proposal.md
    template: proposal.md
    requires: []
    tracks: [B, C]                      # BỔ SUNG 1: yêu cầu theo từng track
    instruction: |
      ...
  - id: spec
    generates: "spec/**/*.md"
    template: spec.md
    requires: [proposal]
    tracks: [B?, C]                     # B? = chỉ bắt buộc nếu hành vi thay đổi
    reads:                              # BỔ SUNG 2: hợp đồng ngữ cảnh tường minh
      - changes/${change}/proposal.md
      - docs/system/specs/${capability}/spec.md
    instruction: |
      ...
  - id: impact
    generates: impact.md
    requires: [spec]
    tracks: [C]
    reads:
      - changes/${change}/spec/**
      - derived: [deps, inventory]
      - claims: metadata
  - id: design
    generates: design.md
    requires: [spec, impact]
    tracks: [C]
    reads:
      - changes/${change}/spec/**
      - changes/${change}/impact.md
      - claims: "${impact.claims_touched}"
  - id: tasks
    generates: tasks.md
    requires: [spec, impact, design]
    tracks: [B, C]
apply:
  requires: [tasks]
  tracks: tasks.md
```

**Bổ sung 1 (`tracks`)** là bộ định tuyến quy mô được biểu diễn dưới dạng dữ liệu. Cùng một DAG phục vụ cho tất cả các track; track sẽ lựa chọn node nào là bắt buộc. Điều này tránh việc phải duy trì các workflow hạng nhẹ và hạng nặng riêng biệt, vốn là cách mà GSD đi đến việc phân nhánh thành các lệnh `quick`, `fast`, `sketch`, `spike` và `do` riêng biệt.

**Bổ sung 2 (`reads`)** biến kỹ nghệ ngữ cảnh thành một đặc tính của mô hình dữ liệu thay vì của prompt. Lệnh `forge instructions <id> --change N --json` phân giải nó — bao gồm các bộ chọn `claims:`, mở rộng ra nội dung cụ thể của từng claim — để một phase chỉ nạp chính xác hợp đồng của nó. Đây là điểm khác biệt cấu trúc quan trọng nhất so với mọi framework ưu tiên prompt trong tài liệu tham chiếu.

**Vòng đời của Artifact.**

| Phân lớp | Các Artifact | Tuổi thọ | Chủ sở hữu | Kiểm định bởi |
|---|---|---|---|---|
| **Vĩnh viễn (Permanent)** | các claim `docs/system/**`, các ADR, spec năng lực vĩnh viễn, `OVERVIEW.md` | vĩnh viễn | con người (agent đề xuất) | `forge check --scope store` |
| **Phái sinh (Derived)** | `docs/system/derived/**` | cho đến commit tiếp theo làm thay đổi đầu vào | `forge sync derived` | tái tạo đồng nhất từng byte |
| **Sổ cái (Ledger)** | `DRIFT.md`, `DEBT.md` | các mục sống đến khi được giải quyết hoặc miễn trừ; các tệp là vĩnh viễn | kernel ghi thêm, con người giải quyết | `forge check` |
| **Tạm thời (Temporary)** | `changes/NNNN/**` | đến khi `converge`, sau đó lưu trữ ở chế độ chỉ đọc | change đó | `forge gate <point>` |
| **Phù du (Ephemeral)** | `.forge/cache/**`, trajectory giữa phiên chạy | có thể bỏ đi / được lưu trữ cùng change | kernel | không kiểm định |

**Đánh phiên bản.** Các spec vĩnh viễn và các claim được quản lý phiên bản bởi chính git, không phải bởi một trường version trong tệp — một trường version trong một tệp mà git đã quản lý phiên bản là nguồn chân lý thứ hai thừa thãi. Các ADR là bất biến một khi đã được chấp thuận và chỉ có thể bị *thay thế (superseded)*, không bao giờ chỉnh sửa trực tiếp. `.forge/schema/*.yaml` mang một số nguyên `version` để kernel có thể từ chối một schema mà nó không hiểu.

**Lưu trữ (Archival).** Lệnh `converge` di chuyển `changes/NNNN/` sang `changes/archive/YYYY-MM-DD-NNNN-<slug>/` một cách nguyên vẹn, bao gồm cả `verification.json` và các file trajectory. Các bản lưu trữ là chỉ-đọc theo quy ước và không bao giờ là đầu vào cho bất kỳ phase nào — nếu một điều gì đó trong kho lưu trữ có ý nghĩa cho tương lai, nó thuộc về tầng vĩnh viễn, đó chính là kỷ luật mà cơ chế gập lưu trữ (archive fold) thực thi.

### 4.2 Mô hình Skill

```markdown
---
name: assess-impact
phase: impact
requires-kernel: ["forge impact", "forge trace"]
reads: from-dag                     # hợp đồng `reads` của DAG nắm thẩm quyền tối cao
writes: ["changes/${change}/impact.md"]
---
```

Các quy tắc cho mọi skill, mỗi quy tắc đều có lý do:

- **≤ 250 dòng.** Vượt quá mức đó, quy trình đang làm quá nhiều việc và nên được chia nhỏ hoặc chuyển bớt vào kernel. Hai skill dài nhất của Superpowers (568 và 679 dòng) chính là hai skill kém sắc nét nhất của nó.
- **Ưu tiên kernel trước.** Một skill bắt buộc phải gọi kernel cho bất kỳ thứ gì có thể tính toán được và không được tự suy ra bằng văn xuôi. "Kiểm tra xem mọi requirement đã có task chưa" là việc của `forge check`, không phải là một đoạn văn bản chỉ dẫn.
- **Không dùng ngôn ngữ cưỡng chế.** Không dùng chữ in hoa, không nói "bạn không có sự lựa chọn". Nếu cần đến điều đó, nó cần một cổng kiểm soát (gate).
- **Kiểm thử chịu tải (Pressure-tested).** Mỗi skill được phát hành kèm các kịch bản trong `tests/skills/<name>/` vốn sẽ thất bại nếu không có skill và thành công khi có skill (tiếp thu toàn bộ phương pháp luận `writing-skills` của Superpowers — đó là lý do duy nhất để tin rằng một prompt thực sự tạo ra tác động).
- **Công bố khi bước vào.** Một dòng thông báo duy nhất, để bản ghi chép phiên làm việc (transcript) ghi nhận rõ quy trình nào đã chạy.

### 4.3 Mô hình Workflow

Một workflow là một bộ ba `(schema, gates, track policy)`. Thêm một workflow đồng nghĩa với việc thêm một tệp YAML, không phải viết thêm code. Đây là đặc tính giúp harness giữ được kích thước nhỏ gọn ngay cả khi mở rộng quy mô.

### 4.4 Mô hình Trạng thái (State model)

Không có tệp trạng thái nào. Mọi thứ đều được tính toán động:

| Câu hỏi | Tính toán từ |
|---|---|
| Artifact nào đã hoàn thành? | Đường dẫn trong `generates` tồn tại (OpenSpec) |
| Thứ gì đang bị chặn? | Danh sách `requires` của DAG trừ đi tập hợp đã hoàn thành |
| Track hiện tại là gì? | `changes/NNNN/.forge.yaml` |
| Task nào đã xong? | Các ô `- [x]` trong `tasks.md` |
| Tri thức có bị lỗi thời không? | Fingerprint của anchor so với `@sha`; `generated_from_commit` so với HEAD |
| Những gì đang mở chưa giải quyết? | Các mục trong `DRIFT.md` + `DEBT.md` chưa có phán quyết hoặc chưa hết hạn miễn trừ |
| X đang tham chiếu đến cái gì? | `derived/trace.json`, được tạo lại từ các đợt quét |

Hệ quả: không có lộ trình nâng cấp phức tạp cho định dạng trạng thái; không có tình trạng mất đồng bộ; thao tác `git checkout` một commit cũ sẽ mang lại chính xác trạng thái harness của commit đó; và hai người (hoặc hai phiên làm việc) không bao giờ tranh chấp một tệp lockfile.

### 4.5 Mô hình Kiểm định (Validation model)

Ba tầng, và phân tầng quyết định ai có quyền hành động dựa trên một phát hiện.

| Tầng | Triển khai dưới dạng | Ví dụ | Hệ quả |
|---|---|---|---|
| **Cấu trúc (Structural)** | Các bộ parser của kernel | các trường của claim, ngữ pháp spec, tính duy nhất/đơn điệu của ID, quét placeholder, thứ tự DAG | **ERROR** — chặn cổng kiểm soát |
| **Quan hệ (Relational)** | kernel + `trace.json` | độ bao phủ requirement ↔ task ↔ test, tính trọn vẹn của claim-touch, giải quyết bằng chứng, tham chiếu ngược quy tắc, ngân sách | **ERROR** — chặn cổng kiểm soát |
| **Ngữ nghĩa (Semantic)** | LLM thông qua một skill | điều này có kiểm thử được không, hai mục này có cùng ý nghĩa không, quy tắc này có thực thi được không, đây có phải phán quyết độ lệch đúng không | **FINDING** — mang tính tư vấn; chỉ con người mới có quyền biến nó thành một lệnh chặn |

Ranh giới phân tầng là canh bạc cốt lõi của thiết kế: **bất cứ điều gì có thể hạ xuống một tầng thấp hơn, bắt buộc phải hạ xuống.** Một kiểm tra ngữ nghĩa trở thành kiểm tra quan hệ (bằng cách đưa ra quy ước ID) hoặc cấu trúc (bằng cách đưa ra một trường dữ liệu) là một cải tiến vĩnh viễn; điều ngược lại là một sự thoái lùi vĩnh viễn.

Định dạng của một Issue, tiếp thu từ OpenSpec:

```json
{"level": "ERROR", "code": "store.anchor_missing", "path": "docs/system/domain.md",
 "line": 84, "claim": "INV-7", "message": "anchor src/payments/refund.ts#computeRefundable no longer exists",
 "fix": "forge reanchor INV-7, or forge retire INV-7 --ground 1"}
```

Mọi ERROR đều mang một trường `fix` nêu tên lệnh để giải quyết nó. Một thông điệp lỗi không có hành động tiếp theo sẽ rèn luyện cho người dùng thói quen phớt lờ các lỗi.

---

## 5. Giao diện giữa các tầng

### 5.1 Kernel → skill

JSON trên stdout, một định dạng duy nhất, luôn luôn như vậy. Các skill phân tích cú pháp nó; chúng không bao giờ phân tích đầu ra được định dạng cho người đọc.

```json
{"ok": false, "command": "forge check --scope change --change 4",
 "summary": {"errors": 2, "warnings": 5, "findings": 0},
 "issues": [ ... ],
 "next": ["forge impact --change 4", "forge check --scope change --change 4"]}
```

### 5.2 Skill → kernel

Các skill chỉ gọi các lệnh đã được tài liệu hóa. Chúng không bao giờ tự ghi vào `derived/`, không bao giờ sửa trực tiếp `DRIFT.md`, và không bao giờ đóng dấu lại một neo bằng tay — những lộ trình đó chỉ tồn tại thông qua kernel, điều này giúp cho dữ liệu xuất xứ trở nên có ý nghĩa.

### 5.3 Host → harness

Hai điểm tích hợp, cả hai đều là tùy chọn và đều rất mỏng:

1. **Bắt đầu phiên làm việc**: nạp `docs/system/OVERVIEW.md` + chỉ mục claim + đầu ra của `forge status`. Đó là tập hợp nạp-liên-tục, và nó luôn nằm trong ngân sách 400 dòng theo thiết kế.
2. **Bắt đầu một phase**: skill gọi `forge instructions <artifact> --change N --json` và chỉ nạp chính xác các tệp được trả về.

Nếu host hỗ trợ các hook, có một hook rất đáng để cài đặt: một pre-commit hook chạy `forge check --scope store`, để một kho lưu claim bị hỏng không thể được commit vào git. Mọi thứ khác mà harness cần, nó đạt được thông qua việc được gọi trực tiếp.

---

## 6. Các lựa chọn công nghệ triển khai

**Ngôn ngữ: Python 3.11+, ưu tiên thư viện chuẩn (stdlib-first).** Lý do: harness phải chạy được trên các repository thuộc bất kỳ ngôn ngữ nào, vì vậy runtime của chính nó phải là thứ ít gây phiền hà nhất; Python có mặt hoặc dễ dàng cài đặt ở khắp mọi nơi; `uv run` giúp việc chạy một script đơn tệp với metadata dependency nội dòng trở nên khả thi trong thực tế (BMAD đã làm chính xác điều này cho `lint_spine.py`); và `py-tree-sitter` là con đường trực tiếp nhất để tạo ra các fingerprint neo mà mọi thứ phụ thuộc vào.

**Ngân sách dependency: tối đa hai.** `tree-sitter` (+ các gói ngữ pháp) và một parser YAML. Mọi thứ khác đều là thư viện chuẩn và các lệnh gọi `subprocess` tới các công cụ mà dự án đã có sẵn. Nếu không có sẵn `tree-sitter`, các neo sẽ hạ cấp xuống thành các chuỗi băm nội dung đã chuẩn hóa khoảng trắng và được báo cáo là `coarse: true` — harness vẫn hoạt động trơn tru với 0 dependency bên thứ ba, chỉ là độ chính xác kém hơn một chút.

**Hỗ trợ đa nền tảng ngay từ ngày đầu.** Môi trường làm việc của lập trình viên ở đây là Windows với PowerShell và Git Bash. Do đó: không dùng script chỉ chạy được trên bash trong kernel (Spec Kit phải duy trì các bản song song bash/PowerShell/Python cho mọi script — một gánh nặng bảo trì thực sự mà chúng ta tránh được bằng cách chỉ có một bản triển khai bằng Python duy nhất); dùng `pathlib` ở mọi nơi; không bao giờ ngầm định dấu gạch chéo `/`; git được gọi với các đối số tường minh và không bao giờ qua một chuỗi shell; và bất kỳ giá trị lưu trữ nào truyền tới `git` đều phải được kiểm định trước (GSD xác thực `built_at_commit` là 4–40 ký tự hex chính vì một file `graph.json` độc hại có thể tiêm các tùy chọn argv — chúng ta áp dụng quy tắc đó cho mọi SHA và đường dẫn của neo).

**Không dùng Go/Rust cho v1**, dù việc biên dịch thành một file nhị phân duy nhất rất hấp dẫn: nó làm chậm tốc độ lặp cải tiến mà thiết kế này cần trong khi định dạng claim vẫn đang trong quá trình thử nghiệm. Xem xét lại một khi định dạng đã sống sót qua vài tháng sử dụng thực tế.

**Kiểm thử chính harness.** Kernel nhận các bài test đơn vị thông thường và kiểm thử golden-file trên các repository mẫu (bao gồm cả fixture đường dẫn Windows). Các skill nhận các bài kiểm thử áp lực: một kịch bản, một lần chạy baseline không có skill bắt buộc phải fail, và một lần chạy có skill bắt buộc phải pass. Một skill không có baseline thất bại là một skill chưa được chứng minh và sẽ không được xuất xưởng.

---

## 7. Những gì kiến trúc này từ chối trở thành

| Bị từ chối | Lý do |
|---|---|
| Một nền tảng đa-agent (multi-agent platform) | Subagent là các ranh giới ngữ cảnh. Nhân cách (personas) chỉ là trang phục hóa trang. Năm nhân cách của BMAD thực chất chỉ là năm skill đội những chiếc mũ khác nhau |
| Một cơ sở dữ liệu đồ thị (graph database) | GSD đã xây dựng một cái; nó trở thành cách biểu diễn thứ tư của hệ thống mang theo sự mục rữa của riêng nó |
| Một MCP server | Kernel là một CLI. Một CLI có thể kết hợp với mọi host; một server đòi hỏi một vòng đời, một phiên bản giao thức, và một lý do tồn tại |
| Một IDE hoặc trình soạn thảo tùy biến | Không có gì ở đây cần giao diện UI. `forge status` là một màn hình văn bản duy nhất |
| Một execution engine | mini-SWE-agent chỉ có ~200 dòng và vẫn đầy tính cạnh tranh. Host đã có sẵn một engine rồi |
| Một lớp trừu tượng client/nhà cung cấp mô hình | Kernel không bao giờ gọi mô hình. Đó chính là mấu chốt |
| Một hệ thống plugin | Chín skills, mười hai gates, năm schemas. Một hệ thống plugin cho ngần ấy thứ sẽ là một bộ máy cồng kềnh hơn cả cỗ máy chính. Các dự án mở rộng thông qua `config.yaml` (`rules`, `gates`, `commands`) và bằng cách ghi đè template |
| Một trang web tài liệu song song | Kho lưu trữ là markdown trong git. Nếu cần hiển thị, nền tảng lưu trữ git đã render sẵn markdown rồi |
| Một DSL điều phối riêng | DAG chỉ là 40 dòng YAML với ba trường dữ liệu. Bất cứ thứ gì phức tạp hơn sẽ biến thành một ngôn ngữ mà không ai có thể debug nổi |

---

## 8. Ngân sách tăng trưởng (Growth budget)

Bài học rõ ràng nhất từ tài liệu tham chiếu là các framework này tăng trưởng nhanh hơn các dự án mà chúng phục vụ — GSD phình to lên 44 capabilities và ~90 workflows, BMAD lên 29 skills và 2.4 MB. Do đó, các con số là một phần của kiến trúc, và việc thay đổi một con số là một quyết định đòi hỏi lý do được ghi lại trong [CONSTITUTION.md](CONSTITUTION.md).

| Ngân sách | v1 | Mức trần cứng | Phải làm gì khi chạm trần |
|---|---|---|---|
| Skills | 9 | 12 | Gộp hai skill hoặc xóa một skill trước khi thêm mới |
| Các lệnh của Kernel | ~20 | 25 | Ưu tiên thêm cờ (flag) trên một lệnh đã có |
| Cổng kiểm soát (Gates) | 12 | 16 | Xóa một cổng chưa từng kích hoạt lần nào |
| Lược đồ Workflow | 5 | 7 | Biểu diễn biến thể dưới dạng một track, không phải một schema mới |
| Số dòng code Kernel (LOC) | — | ~3.000 | Vượt quá mức này, kernel đang làm công việc phán đoán; hãy tìm nó và chuyển sang một skill |
| Số dòng cho mỗi Skill | — | 250 | Chia nhỏ ra, hoặc chuyển phần có thể tính toán được vào kernel |
| Số dòng nạp-liên-tục | — | 400 | Cắt giảm bớt hoặc di dời bớt claim. **Tuyệt đối không bao giờ nâng ngân sách** |
