# FastAPI İşe Alım API'si

Bu proje, FastAPI, Oracle DB ve Upstash Redis kullanılarak geliştirilmiş bir işe alım portalı API'sidir. Kullanıcıların kaydolmasına, iş ilanları oluşturmasına, işlere başvurmasına ve mülakatları yönetmesine olanak tanır.

## Özellikler

* **Kullanıcı Yönetimi:** Kayıt olma, giriş yapma ve farklı kullanıcı rolleri (Admin, Recruiter, Candidate).
* **İş İlanları Yönetimi:** İş ilanı oluşturma, görüntüleme, güncelleme ve silme (yetkilendirme ile).
* **Başvuru Yönetimi:** İşlere başvurma, başvuruları görüntüleme, güncelleme ve silme (yetkilendirme ile).
* **Mülakat Yönetimi:** Mülakat planlama, görüntüleme, güncelleme ve silme (yetkilendirme ile).
* **Rol Bazlı Yetkilendirme:** Farklı kullanıcı rolleri için farklı yetkilendirme seviyeleri.
* **Rate Limiting:** Upstash Redis kullanılarak API istekleri için hız sınırlaması.
* **Docker Desteği:** `docker-compose.yaml` dosyası ile kolay kurulum ve çalıştırma[cite: 1].

## Kullanılan Teknolojiler

* **Backend Framework:** FastAPI
* **Veritabanı:** Oracle DB
* **Cache & Rate Limiting:** Upstash Redis
* **API Test:** Uvicorn
* **Veri Doğrulama:** Pydantic
* **Konteynerizasyon:** Docker [cite: 1]

## Kurulum ve Çalıştırma

### Gereksinimler

* Python 3.x
* Docker ve Docker Compose
* Oracle Database (Çalışan bir örneği veya Docker imajı)
* Upstash Redis hesabı ve bağlantı bilgileri

### Adımlar

1.  **Repository'yi Klonlayın:**
    ```bash
    git clone <repository-url>
    cd <repository-adı>
    ```

2.  **Oracle Network Oluşturun (Eğer yoksa):**
    ```bash
    docker network create oracle-network
    ```
    *Not: Oracle veritabanınız farklı bir network üzerinde çalışıyorsa `docker-compose.yaml` dosyasını [cite: 1] ve `main.py` dosyasındaki DSN bilgisini güncellemeniz gerekebilir.*

3.  **Çevre Değişkenlerini Ayarlayın:**
    `docker-compose.yaml` dosyasındaki [cite: 1] `environment` bölümünü kendi Oracle DB bilgilerinizle güncelleyin:
    ```yaml
    environment:
      - ORACLE_USER=<oracle_kullanici_adiniz>
      - ORACLE_PASSWORD=<oracle_sifreniz>
      - ORACLE_DSN=<oracle_dsn_bilginiz> # Örnek: localhost/XE veya oracle-db-container-name/XE
    ```
    Ayrıca, `main.py` dosyasındaki Upstash Redis URL ve Token bilgilerinizi güncelleyin:
    ```python
    redis_client = redis.Redis(url="<upstash_redis_url>", token="<upstash_redis_token>")
    ```

4.  **Docker Compose ile Çalıştırın:**
    ```bash
    docker-compose up --build
    ```

5.  API'ye `http://localhost:8000` adresinden erişebilirsiniz. FastAPI'nin otomatik Swagger dokümantasyonuna `http://localhost:8000/docs` adresinden ulaşabilirsiniz.

## API Endpoints

* `POST /register`: Yeni kullanıcı kaydı.
* `POST /login`: Kullanıcı girişi ve token alma.
* `POST /jobs`: Yeni iş ilanı oluşturma (Admin, Recruiter yetkisi).
* `GET /jobs`: Tüm iş ilanlarını listeleme.
* `PUT /jobs/{job_id}`: İş ilanını güncelleme (Admin, Recruiter yetkisi).
* `DELETE /jobs/{job_id}`: İş ilanını silme (Admin yetkisi).
* `POST /apply`: Bir işe başvurma (Candidate yetkisi).
* `GET /applications`: Tüm başvuruları listeleme (Admin, Recruiter yetkisi).
* `PUT /applications/{application_id}`: Başvuruyu güncelleme (Admin, Recruiter yetkisi).
* `DELETE /applications/{application_id}`: Başvuruyu silme (Admin yetkisi).
* `POST /interviews`: Mülakat planlama (Admin, Recruiter yetkisi).
* `GET /interviews`: Tüm mülakatları listeleme (Admin, Recruiter yetkisi).
* `PUT /interviews/{interview_id}`: Mülakatı güncelleme (Admin, Recruiter yetkisi).
* `DELETE /interviews/{interview_id}`: Mülakatı silme (Admin yetkisi).
* `PUT /users/{user_id}`: Kullanıcı bilgilerini güncelleme (Admin yetkisi).
* `DELETE /users/{user_id}`: Kullanıcıyı silme (Admin yetkisi).
