# BAO CAO DE TAI AI CHO E-COMMERCE

## De tai
Phan tich hanh vi khach hang de tu van dich vu trong he thong e-commerce sach theo kien truc microservice.

## Tac gia
Sinh vien thuc hien: (dien ten)

Giang vien huong dan: (dien ten thay/co)

Thoi gian: 2026

---

## Tom tat
Bao cao nay trinh bay day du qua trinh khao sat va trien khai ung dung AI trong he thong e-commerce (bookstore microservice). Bai lam duoc xay dung theo 4 nhom yeu cau chinh:

1. Khao sat cac ap dung AI trong e-commerce.
2. Xay dung mo hinh deep learning `model_behavior` de phan tich hanh vi khach hang.
3. Xay dung Knowledge Base (KB) de bo sung tri thuc cho tu van.
4. Ap dung RAG de xay dung chat tu van va tich hop vao he thong e-commerce.

He thong trien khai theo kieu 2 lop AI:

- `behavior-ai-service`: hoc va suy dien hanh vi (customer profile + candidate books).
- `recommender-ai-service`: dong vai tro advisor layer (KB + retrieval + rerank + generation).

Frontend tuong tac thong qua `api-gateway`, cho phep nguoi dung xem goi y va dat cau hoi tu van ngay tren trang recommendations.

---

## 1. Khao sat cac ap dung AI trong e-commerce (phan tong quan)

### 1.1. Dong luc ung dung AI trong e-commerce
E-commerce hien dai doi mat voi 3 bai toan cot loi:

- Da dang nguoi dung va hanh vi mua sam (moi nguoi mot so thich, mot muc gia, mot thoi diem).
- So luong san pham lon, kho tim dung san pham phu hop.
- Nhu cau trai nghiem ca nhan hoa theo thoi gian thuc.

AI duoc ap dung de giai 3 bai toan tren bang cach:

- Hieu nguoi dung sau hon (profiling, segmentation, prediction).
- Tang toc do tim kiem va ra quyet dinh (recommendation, conversational commerce).
- Toi uu van hanh va doanh thu (pricing, inventory, fraud, logistics).

### 1.2. Cac nhom ung dung AI pho bien trong e-commerce

#### 1.2.1. Recommendation va personalization
Day la nhom ung dung pho bien nhat. Muc tieu la dua ra danh sach san pham co kha nang duoc mua cao nhat.

Huong tiep can thuong gap:

- Rule-based: luat nghiep vu don gian (san pham cung danh muc, top ban chay, top rating).
- Collaborative filtering: dua tren hanh vi nhom nguoi dung tuong tu.
- Content-based: dua tren thuoc tinh san pham + profile nguoi dung.
- Deep learning recommender: hoc embedding user/item, ket hop nhieu nguon signal.
- Hybrid recommender: ket hop nhieu cach de tang do on dinh.

Gia tri mang lai:

- Tang conversion rate.
- Tang average order value.
- Tang retention nhờ trai nghiem phu hop.

#### 1.2.2. Search thong minh va semantic retrieval
Thay vi tim kiem theo tu khoa chinh xac, AI cho phep tim kiem theo y nghia.

Vi du:

- Nguoi dung go "sach backend de doc de hieu", he thong van tra ra sach API/Django co review phu hop.
- Kha nang chinh ta va xu ly tu dong nghia.
- Query understanding theo y dinh (muc gia, cap do, chu de).

Thanh phan ky thuat:

- NLP tokenization, intent detection.
- Dense retrieval/embedding (neu he thong lon).
- Hybrid lexical + semantic retrieval.

#### 1.2.3. Chatbot/AI advisor (conversational commerce)
AI chat duoc dung de:

- Tu van san pham theo nhu cau.
- Giai dap thong tin van chuyen, thanh toan, doi tra.
- Huong dan so sanh san pham.

Huong hien dai la ket hop chatbot voi recommendation va RAG de:

- Dua ra cau tra loi co ngu canh.
- Han che "ao tuong" bang context retrieval.
- Tao ly do goi y minh bach (why recommended).

#### 1.2.4. Dynamic pricing va promotion optimization
AI du doan do nhay gia cua tung nhom khach hang, de toi uu:

- Gia ban theo tung thoi diem.
- Khuyen mai ca nhan hoa.
- Can bang giua doanh thu va ton kho.

Luu y: phai kiem soat fairness va tinh minh bach de tranh phan ung tieu cuc tu nguoi dung.

#### 1.2.5. Demand forecasting va inventory planning
AI du doan nhu cau theo:

- Mua vu.
- Su kien.
- Xu huong marketing.
- Hanh vi mua lap lai.

Tac dong:

- Giam out-of-stock.
- Giam ton kho chet.
- Cai thien planning cho procurement va logistics.

#### 1.2.6. Fraud detection va risk scoring
Trong e-commerce, gian lan co the xay ra o:

- Thanh toan.
- Tai khoan moi.
- Voucher abuse.
- Chargeback.

AI phat hien bat thuong thong qua:

- Pattern recognition.
- Graph features.
- Real-time risk scoring.

#### 1.2.7. Customer analytics va churn prediction
AI dung de:

- Doan kha nang roi bo (churn).
- Xac dinh CLV (customer lifetime value).
- Kich hoat campaign giu chan dung doi tuong.

#### 1.2.8. Computer vision trong e-commerce
Voi mot so nganh (thoi trang, noi that, my pham), thi giac may tinh ho tro:

- Visual search.
- Similar-item recommendation.
- Virtual try-on.
- Kiem tra chat luong anh san pham.

### 1.3. Kien truc tham chieu AI trong e-commerce
Mot pipeline AI e-commerce thuong gom:

1. Data ingestion: clickstream, orders, cart, reviews, profile.
2. Feature/representation: user features, item features, interaction features.
3. Retrieval: lay candidate nhanh (recall).
4. Ranking/reranking: sap xep lai theo muc tieu.
5. Explanation/generation: tao noi dung tu van.
6. Feedback loop: ghi nhan phan hoi de hoc lien tuc.

Trong bai lam nay, pipeline duoc cai dat theo tinh than tren:

- Retrieval va ranking qua `behavior-ai-service` + `recommender-ai-service`.
- Explanation qua advisor RAG.
- Feedback loop dua tren orders, cart, reviews.

### 1.4. Thach thuc khi dua AI vao he thong thuc te

- Du lieu lech (bias), thieu data voi user moi (cold start).
- MTTD (mean time to data): data den cham, khong dong bo.
- Latency khi goi nhieu microservice.
- Hallucination neu chat model khong co context chat.
- Chi phi van hanh va giám sat model.

Do do can co:

- Co che fallback.
- Co che cache hoặc retrieval quy mo nho.
- Logging, monitoring va quan ly phien ban model.

### 1.5. Lien he voi bai toan de tai
Yeu cau "Phan tich hanh vi khach hang de tu van dich vu" phu hop truc tiep voi xu huong conversational personalization:

- Deep learning model hoc hanh vi de tao profile.
- KB tong hop tri thuc san pham + review.
- RAG de tao cau tra loi tu van co ngu canh.
- Tich hop vao luong mua sam qua giao dien gateway.

---

## 2. Tong quan he thong da implement trong codebase

### 2.1. Nen tang microservice
Codebase su dung Django + DRF, trien khai da dich vu:

- Customer, Book, Cart, Order, Payment, Shipping, Comment-Rate, Catalog, Auth.
- API Gateway cho giao dien va dieu huong.
- RabbitMQ cho event-driven flow.
- Hai service AI: `behavior-ai-service` (port external 8013) va `recommender-ai-service` (port external 8011).

### 2.2. Vai tro cua 2 AI service

- `behavior-ai-service`:
  - Endpoints:
    - `POST /behavior/profile/`
    - `POST /behavior/train/`
    - `GET /behavior/status/`
  - Nhiem vu:
    - Tong hop hanh vi user tu orders, cart, reviews.
    - Huan luyen MLP model.
    - Sinh candidate books va reason codes.

- `recommender-ai-service`:
  - Endpoints:
    - `GET /recommendations/<customer_id>/`
    - `POST /advisor/recommendations/`
  - Nhiem vu:
    - Lay profile tu behavior service.
    - Xay KB theo tung cuon sach.
    - Rerank theo user prompt.
    - Tao cau tra loi advisor (Gemini neu co key, fallback neu khong).

### 2.3. Tich hop UI
`api-gateway` da bo sung:

- `GET /recommendations/<customer_id>/`
- `POST /recommendations/<customer_id>/ask/`

Template `recommendations.html` hien thi:

- `answer_text` (cau tra loi advisor).
- `recommended_books`.
- `reason_codes`, `avg_rating`, tom tat profile.
- Nut hanh dong `+ Cart`, `Reviews`.

---

## 3. Xay dung model_behavior dua tren Deep Learning

### 3.1. Muc tieu model
`model_behavior` duoc thiet ke de:

- Du doan muc do phu hop giua customer va candidate book.
- Xep hang candidate sach theo score.
- Ho tro giai thich qua reason codes va signal summary.

### 3.2. Nguon du lieu va feature engineering
Behavior engine lay du lieu tu:

- `customer-service /customers/`
- `order-service /orders/`
- `cart-service /carts/{customer_id}/`
- `book-service /books/`
- `catalog-service /categories/`
- `comment-rate-service /reviews/`

Signal chinh:

- Lich su mua hang (orders + order items).
- Lich su review/rating.
- Noi dung gio hang hien tai.
- Gia tri don hang, tan suat mua, do gan day.
- Su yeu thich danh muc.

Bo feature so hoc (12 dac trung) trong code:

1. Tong so don hang.
2. So don trong 30 ngay.
3. Tong chi tieu.
4. Gia tri don trung binh.
5. Gia sach trung binh da mua.
6. So ngay tu lan mua cuoi.
7. Tong so luong sach trong gio.
8. So dong item trong gio.
9. So review da viet.
10. Diem rating trung binh da cho.
11. Ty le mua o danh muc ua thich.
12. Ty le mua sach cong nghe.

### 3.3. Tao training set
Mau huan luyen duoc tao theo cap (customer, candidate_book):

- Positive (label = 1):
  - Sach da mua.
  - Sach da review.
  - Sach trong gio.
- Negative (label = 0):
  - Sach chua tuong tac.
  - Uu tien lay mau cung category va them mau category khac.

Du lieu duoc seed san:

- 7 categories.
- 24 books.
- 10 customers.
- 40 orders.
- 80 order items.
- 40 reviews.

### 3.4. Kien truc deep learning
Model tu xay dung bang pure Python (khong dung TensorFlow/PyTorch), gom:

- Embedding:
  - customer embedding dim = 8
  - book embedding dim = 12
  - category embedding dim = 6
- MLP:
  - hidden1 = 24 (ReLU)
  - hidden2 = 12 (ReLU)
  - output sigmoid

Input vector:

- customer embedding
- candidate book embedding
- avg embedding cac sach gan day
- avg embedding category gan day
- numerical feature vector da normalize

Ham kich hoat:

- Hidden layers: ReLU
- Output: Sigmoid

Training:

- Epochs = 25
- Learning rate = 0.02
- Backpropagation duoc cai dat thu cong.

### 3.5. Quan ly artifact va vong doi model
Artifact model luu tai:

- `/app/data/behavior_model.json`

Thong tin luu:

- Mapping index (customer/book/category).
- Embeddings.
- Trong so MLP.
- Mean/std cua feature.
- `dataset_stats`.
- `trained_at`.
- `model_version = behavior-mlp-v1`.

Co che lazy training:

- Khi infer ma chua co artifact, service se tu train neu du data.

### 3.6. Suy dien profile va scoring
Endpoint `POST /behavior/profile/` tra ve:

- `preferred_categories`
- `price_band`
- `signals_summary`
- `candidate_books` (book_id, score, reason_codes)
- `fallback_used`
- `model_version`

Cong thuc score cuoi:

- `final_score = 0.75 * model_score + 0.25 * heuristic_score`

Heuristic co tinh den:

- Khop category ua thich.
- Khop category gan day.
- Khop price band.
- Tin hieu rating.

### 3.7. Co che cold-start va fallback
Neu customer chua co interaction:

- Service dung chien luoc cold start:
  - Chon sach con hang.
  - Xep theo review signal (`avg_rating * 10 + total_reviews`).
  - Co gang da dang category.

Neu model loi/khong kha dung:

- Tu dong fallback sang heuristic.
- Tra `fallback_used = true`.

### 3.8. Nhan xet ky thuat
Diem manh:

- Co hoc may that su (embedding + MLP + training/inference).
- Tu phu duoc pipeline train/predict.
- Co fallback de dam bao tinh san sang.

Han che:

- Chua co offline metrics (AUC, NDCG, Precision@K) trong code.
- Chua co pipeline huan luyen dinh ky theo schedule.
- Quy mo mo hinh nho, phu hop demo/assignment hon production lon.

---

## 4. Xay dung Knowledge Base (KB) cho tu van

### 4.1. Muc tieu KB
KB duoc xay trong `recommender-ai-service` theo dang "on-the-fly structured KB", de:

- Hop nhat tri thuc tu nhieu service.
- Tao context chat de giai thich recommendation.
- Tranh tra loi chung chung.

### 4.2. Nguon tri thuc
Moi book trong candidate list duoc enrich bang:

- Metadata sach tu `book-service`.
- Ten category tu `catalog-service`.
- Tong hop review tu `comment-rate-service /reviews/book/{book_id}/`.
- Behavior score + reason codes tu behavior layer.

### 4.3. Cau truc KB per-book
Mau du lieu KB cho moi sach gom:

- `book_id`, `title`, `author`.
- `category_id`, `category_name`.
- `price`, `price_band`, `stock`.
- `isbn`, `description_short`.
- `review_summary`.
- `positive_themes`, `negative_themes`.
- `reader_fit_summary`.
- `avg_rating`, `total_reviews`.
- `embedding_text` (chuoi text tong hop phuc vu retrieval/generation).
- `behavior_score`, `reason_codes`.

### 4.4. Co che review summarization
He thong phan tich comment review bang keyword buckets:

- practical, clear, backend, productivity, advanced, basic.

Tu do tao:

- Positive themes.
- Negative themes.
- Sentiment summary dua tren `avg_rating`.
- Reader fit summary (beginners, advanced, backend readers...).

Day la cach "lightweight KB synthesis", phu hop quy mo assignment ma van co gia tri giai thich.

### 4.5. Retrieval strategy
Chien luoc retrieval theo huong:

1. Candidate-first:
   - Lay candidate tu behavior service.
2. Bo sung unseen candidates:
   - Quet them sach chua mua neu thieu ung vien.
3. Dedupe:
   - Giu score cao nhat moi book_id.
4. Build KB:
   - Enrich tung ung vien thanh doi tuong KB hoan chinh.

Loi ich:

- Giam khong gian tim kiem.
- Giu duoc tinh ca nhan hoa.
- Tao co so tot cho rerank + generation.

### 4.6. Nhan xet ky thuat
Diem manh:

- KB co cau truc ro rang, de debug va mo rong.
- Tri thuc duoc tong hop da nguon, khong phu thuoc duy nhat vao 1 model.

Han che:

- Chua co vector store rieng.
- KB hien tai tao theo request (chua co cache nang cao).

---

## 5. Ap dung RAG de xay dung chat tu van

### 5.1. Muc tieu
Xay dung chat advisor co kha nang:

- Hieu yeu cau hien tai cua user.
- Van dua tren profile hanh vi lich su.
- Tra loi ngan gon, giai thich duoc vi sao goi y.

### 5.2. Kien truc RAG trong he thong nay
RAG duoc thuc hien theo huong pragmatic:

1. Retrieve:
   - Lay profile + candidate tu behavior layer.
   - Build KB books.
   - Rerank theo query intent.
2. Augment:
   - Tao prompt context gom:
     - Customer profile text.
     - Candidate books text.
     - User request.
3. Generate:
   - Goi Gemini API neu co `GEMINI_API_KEY`.
   - Neu khong, dung fallback answer deterministic.

### 5.3. Query understanding
`AdvisorService` phan tich user prompt:

- `matched_categories`.
- `price_pref` (low/medium/high).
- `reading_level` (beginner/advanced).
- `preference_tags` (backend/practical/productivity/theory).
- `query_terms`, `query_phrases`.
- `strong_intent`.

Co bo stop words Anh-Viet va heuristic phrase matching.

### 5.4. Rerank ket hop profile + query
Final ranking score tren KB books gom:

- Behavior score tu model.
- Bonus neu trung preferred category.
- Bonus neu trung category trong query.
- Bonus neu trung muc gia mong muon.
- Bonus query phrase/term match.
- Bonus beginer/advanced fit.
- Bonus theo avg rating.
- Penalty neu query manh nhung khong match.
- Penalty lon neu out-of-stock.

Sau do service chon top-K (toi da 5) cho output cuoi.

### 5.5. Guardrails prompt
Prompt da co cac rang buoc:

- Chi su dung context duoc cung cap.
- Khong "invent" sach ngoai candidate list.
- Uu tien sach con hang.
- Uu tien current user request neu xung dot voi profile chung.

Day la diem quan trong de giam hallucination.

### 5.6. Fallback generation
Neu Gemini khong hoat dong:

- Service van tra cau tu van co cau truc.
- Van dua duoc danh sach sach de UI render.
- Van giu duoc tinh lien tuc cua user experience.

### 5.7. Dinh nghia output advisor
Payload tra ve gom:

- `answer_text`
- `recommended_books`
- `behavior_summary`
- `sources` (model version, kb_book_ids, ordered_book_ids_filtered)
- `fallback_used`
- `user_prompt`
- payload compatible cu: `recommendations`

### 5.8. Danh gia RAG implementation
Diem manh:

- RAG thuc dung, de van hanh.
- Giai quyet duoc bai toan chat + recommendation trong cung pipeline.
- Co fallback de dam bao availability.

Han che:

- Chua co vector embedding retrieval quy mo lon.
- Chua luu lich su hoi dap da turn (multi-turn memory).
- Chua co context cache theo customer.

---

## 6. Deploy va tich hop trong he thong e-commerce

### 6.1. Docker Compose integration
`docker-compose.yml` da them:

- `behavior-ai-service`:
  - Build tu `./behavior-ai-service`
  - Port `8013:8000`
  - Volume `behavior_data:/app/data`
  - Depends on customer/cart/order/book/catalog/comment-rate.

- `recommender-ai-service`:
  - Build tu `./recommender-ai-service`
  - Port `8011:8000`
  - Env:
    - `GEMINI_API_KEY`
    - `GEMINI_MODEL` (default `gemini-2.5-flash`)
  - Volume `recommender_data:/app/data`
  - Depends on behavior/book/catalog/comment-rate.

- `api-gateway` depends on ca 2 AI services.

### 6.2. Bien moi truong
He thong su dung:

- `GEMINI_API_KEY`
- `GEMINI_MODEL`

Khuyen nghi:

- Khong hard-code key vao repo public.
- Quan ly key qua secret manager hoac bien moi truong CI/CD.

### 6.3. Luong tich hop nghiep vu tren UI
User flow:

1. Nguoi dung vao trang `/recommendations/<customer_id>/`.
2. Gateway goi `POST /advisor/recommendations/`.
3. Recommender lay profile hanh vi, tao KB, rerank, generate answer.
4. UI hien:
   - answer text.
   - danh sach sach de xuat + ly do.
   - thong tin profile tom tat.
5. Nguoi dung co the:
   - dat cau hoi moi qua form `ask`.
   - them sach vao gio.
   - xem reviews.

### 6.4. Quy trinh khoi tao du lieu demo
`data/seed_all.sh` da ho tro seed du lieu cho:

- auth, catalog, book, customer/staff/manager, cart, order/pay/ship, comment-rate.

Tai khoan demo co san trong `data/accounts.md`:

- admin, staff, customer1..customer10.

### 6.5. Kiem thu chuc nang can co
Checklist phu hop voi code hien tai:

1. Train behavior model:
   - Goi `POST /behavior/train/`.
2. Kiem tra status:
   - Goi `GET /behavior/status/`.
3. Kiem tra profile:
   - Goi `POST /behavior/profile/` voi `customer_id`.
4. Kiem tra advisor:
   - Goi `POST /advisor/recommendations/`.
5. Kiem tra UI:
   - Mo trang recommendations, gui prompt, quan sat answer va danh sach goi y.

---

## 7. Phan tich thiet ke theo yeu cau de bai

### 7.1. Yeu cau 1: Khao sat AI trong e-commerce
Da duoc trinh bay o Chuong 1 voi:

- Nhom ung dung.
- Kien truc tham chieu.
- Loi ich va rui ro.
- Lien he bai toan cu the.

### 7.2. Yeu cau 2: Xay dung model_behavior deep learning
Da duoc dap ung boi:

- `behavior-ai-service/app/engine.py`
- MLP embedding + backpropagation.
- Train endpoint + status endpoint + profile endpoint.
- Artifact model co versioning.

### 7.3. Yeu cau 3: Xay dung KB cho tu van
Da duoc dap ung boi:

- `recommender-ai-service/app/services.py`:
  - `_build_kb_books`
  - `_summarize_reviews`
  - KB payload fields day du.

### 7.4. Yeu cau 4: Ap dung RAG cho chat tu van
Da duoc dap ung boi:

- `POST /advisor/recommendations/`.
- Prompt context assembly (`_build_prompt_context`).
- Generation bang Gemini (`_call_gemini`) + fallback.
- UI chat form trong gateway (`recommendations_ask`).

### 7.5. Yeu cau 5: Deploy va tich hop he e-commerce
Da duoc dap ung boi:

- Docker compose wiring.
- Gateway route + template.
- Tich hop end-to-end voi cac service du lieu.

---

## 8. Danh gia tong the va huong phat trien

### 8.1. Diem manh tong the

- Kien truc tach lop ro:
  - Behavior learning.
  - KB + RAG advising.
- Tich hop microservice thuc te, co deploy bang Docker.
- Co fallback va backward compatibility endpoint.
- UI da san sang cho demo nghiep vu.

### 8.2. Han che hien tai

- Chua co bo chi so danh gia recommendation chinh thuc (NDCG, MAP, CTR offline).
- Chua co vector database cho retrieval semantic quy mo lon.
- Chua co A/B testing va online experimentation.
- Prompt va rerank chu yeu rule/heuristic, chua hoc ranking-to-rank.
- Chua co cache va async precompute KB de giam latency.

### 8.3. Huong nang cap de dat muc production

1. Bo sung pipeline danh gia:
   - Offline split theo thoi gian.
   - Metric ranking va calibration.
2. Bo sung feature store:
   - Luu profile snapshots + event stream.
3. Nang cap retrieval:
   - Vector index cho sach + review chunks.
   - Hybrid lexical + dense retrieval.
4. Nang cap ranking:
   - Learning-to-rank model (XGBoost LambdaMART hoac deep ranker).
5. Bo sung observability:
   - Theo doi latency theo tung service.
   - Theo doi fallback ratio.
6. Bao mat:
   - Secret management chuan hoa.
   - Audit logging cho prompt/response.

---

## 9. Ket luan
De tai da duoc thuc hien dung trong tam: "Phan tich hanh vi khach hang de tu van dich vu" tren nen tang e-commerce microservice.

Ket qua dat duoc:

- Da co mo hinh deep learning `model_behavior` de hoc hanh vi.
- Da co KB per-book giup giai thich recommendation.
- Da co RAG advisor chat tich hop profile + prompt + candidate context.
- Da deploy va tich hop vao he thong e-commerce thong qua gateway.

Giai phap hien tai phu hop muc tieu hoc phan va co nen tang tot de phat trien len quy mo production trong cac huong nang cap da de xuat.

---

## Phu luc A - Bang mapping file code quan trong

- Behavior model:
  - `behavior-ai-service/app/engine.py`
  - `behavior-ai-service/app/views.py`
  - `behavior-ai-service/app/urls.py`

- Advisor + KB + RAG:
  - `recommender-ai-service/app/services.py`
  - `recommender-ai-service/app/views.py`
  - `recommender-ai-service/app/urls.py`

- Gateway integration:
  - `api-gateway/gateway/views.py`
  - `api-gateway/gateway/urls.py`
  - `api-gateway/templates/recommendations.html`

- Deploy:
  - `docker-compose.yml`
  - `.env`
  - `data/seed_all.sh`

---

## Phu luc B - Mau payload API advisor

### Request
```json
{
  "customer_id": 1,
  "user_prompt": "I want an easy backend book with practical examples and medium budget",
  "limit": 3
}
```

### Response (rut gon)
```json
{
  "customer_id": 1,
  "answer_text": "...",
  "recommended_books": [
    {
      "book_id": 6,
      "title": "Django for APIs",
      "why_recommended": "...",
      "reason_codes": ["query_term_match", "backend_match"]
    }
  ],
  "behavior_summary": {
    "preferred_categories": ["Technology", "Self Development"],
    "price_band": "medium"
  },
  "sources": {
    "behavior_model_version": "behavior-mlp-v1",
    "kb_book_ids": [6, 7, 4]
  },
  "fallback_used": false
}
```
