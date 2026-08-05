@echo off
set SUPERUSER_NAME=Aras
set SUPERUSER_EMAIL=aras@gmail.com
set SUPERUSER_PASS=1234qwer!@#$

echo ===================================================
echo Memulai Proses Reset Lingkungan Testing...
echo ===================================================

echo [1/3] Membersihkan seluruh memori Cache (Redis)...
docker-compose exec redis redis-cli flushall

echo [2/3] Menghapus seluruh data dari Database...
docker-compose exec web python manage.py flush --no-input

echo [3/3] Membuat akun Superuser otomatis (%SUPERUSER_NAME%)...
docker-compose exec -e DJANGO_SUPERUSER_USERNAME=%SUPERUSER_NAME% -e DJANGO_SUPERUSER_EMAIL=%SUPERUSER_EMAIL% -e DJANGO_SUPERUSER_PASSWORD=%SUPERUSER_PASS% web python manage.py createsuperuser --noinput

echo ===================================================
echo Proses Selesai! Sistem sudah bersih ke titik 0.
echo Silakan eksekusi ulang test suite Postman Anda.
echo ===================================================
pause
