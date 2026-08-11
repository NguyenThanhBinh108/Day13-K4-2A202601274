# Nghiên cứu UI/UX & quyết định thiết kế cho dashboard

Dashboard trong `scripts/dashboard_app.py` không dùng Streamlit/notebook — đây là một web app
tự viết (FastAPI backend + HTML/CSS/JS thuần, không framework, không CDN) để có toàn quyền kiểm soát
UI/UX. Trước khi code, tôi khảo sát UI/UX của các sản phẩm observability/dashboard nổi tiếng, đánh giá
điểm mạnh/yếu, rồi chốt quyết định thiết kế dựa trên đó + trên skill `dataviz` (hệ màu đã kiểm định,
mark spec, quy tắc tương tác).

## 1. Khảo sát sản phẩm tham khảo

### Grafana — chuẩn cho dashboard nhiều panel
Grafana là điểm neo cho "chart-heavy monitoring view" giữ được độ dễ đọc dù có 20+ panel trên màn hình,
nhờ spacing nhất quán (margin ~20px giữa các row, gap ~10px giữa panel) và việc thiết kế luôn bắt đầu
từ câu hỏi "audience là ai, metric nào quan trọng nhất" trước khi vẽ panel ([MetricFire](https://www.metricfire.com/blog/7-best-practices-for-grafana-dashboard-design/)).

- **Điểm mạnh**: mật độ thông tin cao mà vẫn có tổ chức; time picker + variable ở top bar dùng chung
  cho toàn dashboard (đúng nguyên tắc "một hàng filter phía trên, áp dụng cho mọi panel").
  Threshold/ngưỡng luôn hiển thị trực tiếp trên chart (vạch màu), không phải ẩn trong tooltip.
- **Điểm yếu (theo khảo sát dark-mode 2026)**: Grafana bị xem là "retrofit" dark mode từ light mode
  thay vì thiết kế dark-first, dẫn tới bảng màu panel nhiều khi quá rực ("neon rave lights") và một số
  chart khó đọc trên nền tối ([AYDesign](https://www.aydesign.ai/blog/dark-mode-dashboard-design-patterns-2026)).
- **Học theo**: layout dạng lưới panel rõ ràng, threshold vẽ trực tiếp trên chart, 1 hàng filter/time
  range chung. **Tránh**: bảng màu quá nhiều hue rực cùng lúc — dashboard của mình dùng đúng 1 hệ màu
  categorical đã kiểm định (8 hue cố định, không tự chế thêm màu).

### Datadog — nhất quán xuyên suốt nhiều loại dữ liệu
Datadog xây design system riêng gọi là DRUIDS với mục tiêu cụ thể: một hành vi UI (filter, chọn time
range, inspect graph) phải **giống nhau ở mọi nơi trong sản phẩm**, để người dùng "pivot" liền mạch từ
metric sang trace sang log mà không phải học lại UI ([Datadog Engineering](https://www.datadoghq.com/blog/engineering/druids-the-design-system-that-powers-datadog/)).

- **Điểm mạnh**: tính nhất quán là chiến lược UX chính, không phải chi tiết thẩm mỹ — đúng insight cho
  bài lab này vì mục tiêu cuối là nối được Metrics → Traces → Logs.
- **Điểm yếu**: dashboard Datadog nổi tiếng dễ bị quá tải (nhiều widget nhỏ chi tiết) nếu không có
  người quản lý layout — đây là lý do RUBRIC yêu cầu "chỉ giữ 6-8 panel quan trọng ở lớp chính".
- **Học theo**: mọi panel dùng **chung một cách hiển thị threshold, chung một cách hiển thị đơn vị,
  chung một kiểu tooltip** — không để panel này format số khác panel kia.

### Vercel & Linear — "gets out of the way", một accent màu duy nhất
Vercel dashboard mới (rollout 2026-02-25) được đánh giá là thiết kế lấy sự tối giản làm gốc: đen/trắng
làm chủ đạo, font Geist, giảm chrome UI tới mức tối thiểu để "không cản đường người dùng"
([Medium – Vercel's New Dashboard UX](https://medium.com/design-bootcamp/vercel-s-new-dashboard-ux-what-it-teaches-us-about-developer-centric-design-93117215fe31); [Vercel changelog](https://vercel.com/changelog/dashboard-navigation-redesign-rollout)).
Cùng nhóm này, Linear/Supabase được ghi nhận là thiết kế **dark-mode-first** thật sự (không phải light
mode đảo màu): nền xám đậm mềm (`#0E`–`#1A`, không dùng đen tuyệt đối để tránh hiện tượng halation/mỏi
mắt), card không viền mà dùng elevation (đổi độ sáng nền + padding) để phân tách, và chỉ **một** màu
nhấn bão hòa cho hành động chính, còn lại đều làm nhạt màu ([AYDesign](https://www.aydesign.ai/blog/dark-mode-dashboard-design-patterns-2026)).

- **Điểm mạnh**: mật độ cao nhưng vẫn "thở được" nhờ khoảng trắng/tối rộng và phân cấp rõ (một số nổi
  bật, còn lại lùi về nền); rất hợp với dashboard kỹ thuật cần nhìn nhanh (KPI) trước khi đọc chi tiết.
- **Điểm yếu**: khi có nhiều panel dữ liệu dày đặc như observability dashboard, phong cách "tối giản
  tuyệt đối" của Linear có thể thiếu chỗ cho threshold line, breakdown nhiều field — cần kết hợp với
  mật độ kiểu Grafana/Datadog, không copy y nguyên.
- **Học theo**: nền tối `#0e0e0d`/`#1a1a19` (không đen tuyệt đối), card phân tách bằng elevation + viền
  hairline rất mờ (không viền đậm), toàn bộ text số liệu dùng font hệ thống, không dùng font trang trí.

### Kết luận sau khảo sát
Không sản phẩm nào là "đúng hoàn toàn" — quyết định cuối: **mật độ thông tin kiểu Grafana/Datadog** (vì
đây là dashboard kỹ thuật, cần đủ 6 panel + threshold + breakdown) + **ngôn ngữ thị giác dark-mode-first
kiểu Linear/Vercel** (nền xám đậm mềm, 1 accent, card borderless-nhưng-có-hairline, ít chrome) +
**tính nhất quán xuyên suốt kiểu Datadog/DRUIDS** (mọi panel format số/threshold/tooltip giống nhau).

## 2. Vì sao không dùng Streamlit (và không dùng thư viện chart ngoài)

- Yêu cầu rõ của nhóm: không Streamlit.
- Không dùng chart library qua CDN (Chart.js, D3 từ CDN...) vì buổi chấm có thể không có mạng ổn định
  — dashboard phải tự chạy được 100% offline. Chart được vẽ bằng SVG thuần trong `app.js`, tự tính toạ
  độ từ dữ liệu — không phụ thuộc file ngoài nào ngoài chính `data/logs.jsonl`.
- Backend là FastAPI (đã có sẵn trong `requirements.txt`, không thêm dependency mới) chỉ đọc
  `data/logs.jsonl` và trả JSON; không đụng tới `app/` (thuộc sở hữu P1/P2/P3).

## 3. Áp dụng hệ thống màu/mark đã kiểm định (skill `dataviz`)

Không tự chọn màu bằng mắt — dùng đúng bảng màu tham chiếu đã qua kiểm định CVD (colorblind-safe) của
skill `dataviz`:

- **Categorical** (8 hue cố định thứ tự: blue, orange, aqua, yellow, magenta, green, violet, red) —
  dùng cho breakdown `error_type` và 2 field `tokens_in`/`tokens_out`.
- **Sequential** (1 hue blue, sáng→đậm) — dùng cho traffic, cost (đại lượng, không phải danh mục),
  luôn là một dải xanh nhạt→đậm duy nhất, không pha nhiều hue kiểu rainbow.
- **Status** (good/warning/serious/critical, bảng màu cố định riêng, luôn kèm icon + label, không
  bao giờ chỉ dùng màu) — dùng cho trạng thái threshold breach của từng panel và banner incident.
- **Diverging** (blue ↔ red, mid-point xám) — không cần dùng trong 6 panel này (không có đại lượng
  "trên/dưới baseline hai chiều").
- Nền/chữ theo đúng token trong `palette.md`: surface sáng `#fcfcfb` / tối `#1a1a19`, ink chính
  `#0b0b0b` / `#ffffff`, gridline hairline 1px không nét đứt (tránh anti-pattern "dashed gridlines").
- Mark spec: line 2px, bar dày ≤24px với đầu bo 4px, marker ≥8px có viền surface 2px, khoảng cách 2px
  giữa các segment/bar liền kề — không vẽ border quanh mark để tách (đúng anti-pattern cần tránh).
- Mọi chart ≥2 series có legend; số liệu không đặt hết trên mỗi điểm (chỉ label điểm cuối/điểm cực trị);
  hover có tooltip nhưng tooltip không phải cách DUY NHẤT để đọc số — số liệu chính vẫn hiển thị ở stat
  tile/label trực tiếp.

## 4. Cấu trúc màn hình đã dựng

```text
┌─────────────────────────────────────────────────────────────────┐
│ Day 13 AI Observability          [● HEALTHY/DEGRADED]  ⏱ 30s ↻  │  ← top bar: trạng thái tổng, refresh
├─────────────────────────────────────────────────────────────────┤
│ [Traffic] [P95 Latency] [Error rate] [Cost] [Tokens] [Quality]  │  ← KPI row: 6 stat tile + sparkline
├─────────────────────────────────────────────────────────────────┤
│ Latency (p50/p95/p99, line + SLO line)  │  Traffic (bar/phút)   │
│ Errors (bar + breakdown error_type)     │  Cost (bar/phút+total)│
│ Tokens (stacked bar in/out)             │  Quality (line + SLO) │
└─────────────────────────────────────────────────────────────────┘
```

- Top bar có pill trạng thái tổng (HEALTHY màu `good` / DEGRADED màu `critical`) tính từ việc có panel
  nào breach threshold hay không — trả lời ngay câu "có đang ổn không" trước khi phải đọc từng số,
  giống cách Grafana/Datadog luôn có một dấu hiệu tổng quan ở đầu dashboard.
- Mỗi panel lớn có: tên panel, đơn vị, time range ("60 phút gần nhất"), đường threshold vẽ trực tiếp
  trên chart kèm nhãn số threshold (không chỉ ẩn trong tooltip) — đúng yêu cầu contract
  "ghi rõ đơn vị… có threshold/SLO line" trong [docs/dashboard-spec.md](dashboard-spec.md).
- Light/dark theme đều được định nghĩa đầy đủ theo `prefers-color-scheme` + nút toggle thủ công (theo
  đúng khuyến nghị "dark mode is selected, not automatic flip" của skill `dataviz`).

## 5. Nguồn tham khảo

- [7 Best Practices for Grafana Dashboard Design — MetricFire](https://www.metricfire.com/blog/7-best-practices-for-grafana-dashboard-design/)
- [DRUIDS, the design system that powers Datadog — Datadog Engineering](https://www.datadoghq.com/blog/engineering/druids-the-design-system-that-powers-datadog/)
- [Dark mode dashboard design patterns SaaS founders are using in 2026 — AYDesign](https://www.aydesign.ai/blog/dark-mode-dashboard-design-patterns-2026)
- [Vercel's New Dashboard UX: What It Teaches Us About Developer-Centric Design — Medium](https://medium.com/design-bootcamp/vercel-s-new-dashboard-ux-what-it-teaches-us-about-developer-centric-design-93117215fe31)
- [New dashboard redesign is now the default — Vercel changelog](https://vercel.com/changelog/dashboard-navigation-redesign-rollout)
- Skill nội bộ `dataviz` (`references/palette.md`, `color-formula.md`, `marks-and-anatomy.md`,
  `interaction.md`, `anti-patterns.md`, `choosing-a-form.md`) dùng làm chuẩn màu/mark/tương tác.
