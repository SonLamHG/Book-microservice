# Chinh sach cua hang BookStore

## Chinh sach giao hang
- BookStore ho tro 2 phuong thuc giao hang: STANDARD (tieu chuan) va EXPRESS (nhanh).
- Giao hang tieu chuan: 3-5 ngay lam viec, mien phi cho don hang tren 300.000 VND.
- Giao hang nhanh: 1-2 ngay lam viec, phi giao hang 30.000 VND.
- Giao hang toan quoc, bao gom cac tinh thanh xa.
- Ma van don (tracking number) duoc cap tu dong khi don hang chuyen sang trang thai SHIPPING.

## Chinh sach thanh toan
- BookStore chap nhan 3 phuong thuc thanh toan:
  + COD (Thanh toan khi nhan hang): Pho bien nhat, khong mat phi.
  + CREDIT_CARD (The tin dung): Thanh toan truc tuyen an toan.
  + PAYPAL: Thanh toan qua PayPal.
- Don hang se o trang thai RESERVED cho den khi thanh toan hoan tat.
- Sau khi thanh toan, trang thai chuyen sang COMPLETED.

## Chinh sach doi tra
- Khach hang co the yeu cau doi tra trong vong 7 ngay ke tu khi nhan hang.
- Sach phai con nguyen trang thai, chua su dung, con nguyen bao bi.
- Lien he bo phan ho tro qua email hoac dien thoai de yeu cau doi tra.
- Hoan tien trong vong 3-5 ngay lam viec sau khi nhan lai sach.

## Quy trinh dat hang
1. Chon sach va them vao gio hang.
2. Kiem tra gio hang, dieu chinh so luong.
3. Dat hang: chon dia chi, phuong thuc thanh toan, phuong thuc giao hang.
4. He thong tu dong tao don hang, dat cho thanh toan va giao hang.
5. Xac nhan don hang va gui thong bao.
6. Theo doi trang thai don hang: PENDING -> CONFIRMED -> PAID -> SHIPPING -> COMPLETED.

## Ho tro khach hang
- Email: support@bookstore.vn
- Dien thoai: 1900-xxxx (8h-22h hang ngay)
- Chat truc tuyen: Su dung chat widget tren website
