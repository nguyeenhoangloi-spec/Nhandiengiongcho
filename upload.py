# ...existing code...
# upload.py
# Blueprint xử lý upload ảnh và dự đoán

from flask import Blueprint, request, redirect, url_for, flash, render_template, current_app, session, send_file
from predict import ImagePredictor
from werkzeug.utils import secure_filename
import cv2
import numpy as np
import os
from io import BytesIO
import uuid

# --- YOLOv8 integration ---
from ultralytics import YOLO

# --- Database integration ---
from connect import get_connection
from models import PredictionHistory, UserQuota, PaymentOrder
from vietqr import build_vietqr_payload

try:
	import qrcode
except Exception:
	qrcode = None

predict_bp = Blueprint("predict", __name__)
predictor = ImagePredictor()


def _get_session_user_id() -> int | None:
	user_id_raw = session.get("user_id")
	if user_id_raw is None:
		return None
	try:
		return int(user_id_raw)
	except (TypeError, ValueError):
		return None

# Base detection models (COCO dog/cat + optional segmentation)
det_model = YOLO('yolov8n.pt')        # Detection/classification
seg_model = YOLO('yolov8n-seg.pt')    # Segmentation

# Optional: auto-discover YOLOv8 breed model weights (trained locally)
# Scan common locations and any runs/detect/*/weights/best.pt
def _find_breed_weight() -> str | None:
	# direct candidates
	direct_candidates = [
		os.path.join('runs', 'detect', 'breeds', 'weights', 'best.pt'),
		os.path.join('runs', 'detect', 'breeds_from_scratch', 'weights', 'best.pt'),
		os.path.join('weights', 'yolov8_breed_best.pt'),
		os.path.join('models', 'yolov8_breed_best.pt'),
	]

	found: list[tuple[str, float]] = []
	for p in direct_candidates:
		if os.path.exists(p):
			try:
				found.append((p, os.path.getmtime(p)))
			except Exception:
				found.append((p, 0.0))

	# Walk under runs/detect/**/weights/best.pt
	detect_root = os.path.join('runs', 'detect')
	if os.path.isdir(detect_root):
		for dirpath, dirnames, filenames in os.walk(detect_root):
			if 'best.pt' in filenames and os.path.basename(dirpath) == 'weights':
				p = os.path.join(dirpath, 'best.pt')
				try:
					found.append((p, os.path.getmtime(p)))
				except Exception:
					found.append((p, 0.0))

	if found:
		# pick the most recently modified best.pt
		found.sort(key=lambda t: t[1], reverse=True)
		return found[0][0]
	return None

breed_model = None
_bw = _find_breed_weight()
if _bw:
	try:
		breed_model = YOLO(_bw)
	except Exception:
		breed_model = None

# Trang upload ảnh: chỉ hiển thị form nếu đã đăng nhập
@predict_bp.route("/upload-page", methods=["GET"])
def upload_page():
	user_id = _get_session_user_id()
	if user_id is None:
		flash("Vui lòng đăng nhập để sử dụng chức năng này.", "warning")
		return redirect(url_for("login.login"))

	quota_info = None
	try:
		role = session.get("role", "user")
		if role == "user":
			conn = get_connection()
			try:
				quota = UserQuota.get_or_create(conn, user_id)
				total_predictions = PredictionHistory.count_by_user(conn, user_id)
				quota_info = {
					"plan": quota.get("plan", "free"),
					"free_limit": UserQuota.FREE_PREDICTIONS,
					"total_predictions": int(total_predictions or 0),
					"remaining_free": max(0, UserQuota.FREE_PREDICTIONS - int(total_predictions or 0)),
					"ad_views_used": int(quota.get("ad_views_used", 0)),
					"ad_views_limit": UserQuota.MAX_AD_VIEWS,
					"ad_views_remaining": max(0, UserQuota.MAX_AD_VIEWS - int(quota.get("ad_views_used", 0))),
					"ad_unlocks_remaining": int(quota.get("ad_unlocks_remaining", 0)),
				}
			finally:
				conn.close()
	except Exception:
		quota_info = None

	return render_template("upload_page.html", quota_info=quota_info)


@predict_bp.route("/watch-ad", methods=["GET"])
def watch_ad():
	user_id = _get_session_user_id()
	if user_id is None:
		flash("Vui lòng đăng nhập để sử dụng chức năng này.", "warning")
		return redirect(url_for("login.login"))

	# Admin / non-user role bỏ qua
	if session.get("role") != "user":
		return redirect(url_for("predict.upload_page"))

	quota_info = None
	try:
		conn = get_connection()
		try:
			quota = UserQuota.get_or_create(conn, user_id)
			total_predictions = PredictionHistory.count_by_user(conn, user_id)
			quota_info = {
				"plan": quota.get("plan", "free"),
				"free_limit": UserQuota.FREE_PREDICTIONS,
				"total_predictions": int(total_predictions or 0),
				"ad_views_used": int(quota.get("ad_views_used", 0)),
				"ad_views_limit": UserQuota.MAX_AD_VIEWS,
				"ad_views_remaining": max(0, UserQuota.MAX_AD_VIEWS - int(quota.get("ad_views_used", 0))),
				"ad_unlocks_remaining": int(quota.get("ad_unlocks_remaining", 0)),
			}
		finally:
			conn.close()
	except Exception:
		quota_info = None

	return render_template("watch_ad.html", quota_info=quota_info)


@predict_bp.route("/watch-ad/complete", methods=["POST"])
def watch_ad_complete():
	user_id = _get_session_user_id()
	if user_id is None:
		flash("Vui lòng đăng nhập để sử dụng chức năng này.", "warning")
		return redirect(url_for("login.login"))
	if session.get("role") != "user":
		return redirect(url_for("predict.upload_page"))

	conn = None
	try:
		conn = get_connection()
		quota = UserQuota.get_or_create(conn, user_id)
		# Nếu đã nâng gói (không còn free), không cần xem quảng cáo
		if quota.get("plan") != "free":
			return redirect(url_for("predict.upload_page"))

		updated = UserQuota.mark_ad_watched(conn, user_id)
		if updated is None:
			flash("Bạn đã xem đủ 3 lần quảng cáo. Vui lòng mua gói để tiếp tục.", "warning")
			return redirect(url_for("predict.upgrade"))
		flash("Đã mở khóa thêm 3 lượt nhận diện. Bạn có thể tiếp tục!", "success")
		return redirect(url_for("predict.upload_page"))
	except Exception as e:
		print("[ADS] complete error:", e)
		flash("Không thể ghi nhận quảng cáo. Vui lòng thử lại.", "error")
		return redirect(url_for("predict.watch_ad"))
	finally:
		if conn:
			conn.close()


@predict_bp.route("/upgrade", methods=["GET"])
def upgrade():
	if _get_session_user_id() is None:
		flash("Vui lòng đăng nhập để sử dụng chức năng này.", "warning")
		return redirect(url_for("login.login"))
	return render_template("upgrade.html")


def _plan_price_vnd(plan: str) -> int:
	plan = (plan or "").lower()
	if plan == "basic":
		return 49000
	if plan == "pro":
		return 99000
	# enterprise: liên hệ
	return 0


@predict_bp.route("/checkout", methods=["POST"])
def checkout():
	"""Trang thanh toán (có QR) - demo."""
	user_id = _get_session_user_id()
	if user_id is None:
		flash("Vui lòng đăng nhập để sử dụng chức năng này.", "warning")
		return redirect(url_for("login.login"))

	plan = (request.form.get("plan") or "pro").strip().lower()
	payment_method = (request.form.get("payment_method") or "qr").strip().lower()
	allowed_plans = {"basic", "pro", "enterprise"}
	allowed_payments = {"qr", "momo", "vnpay", "bank", "card"}
	if plan not in allowed_plans:
		plan = "pro"
	if payment_method not in allowed_payments:
		payment_method = "qr"

	order_id = uuid.uuid4().hex[:12]
	amount_vnd = _plan_price_vnd(plan)

	# Lưu order vào DB để admin theo dõi + session để xác nhận sau
	conn = None
	try:
		conn = get_connection()
		PaymentOrder.create_order(
			conn,
			order_id=order_id,
			user_id=user_id,
			plan=plan,
			payment_method=payment_method,
			amount_vnd=amount_vnd,
		)
	finally:
		if conn:
			conn.close()

	session["pending_payment"] = {"order_id": order_id}

	return render_template(
		"checkout.html",
		order_id=order_id,
		plan=plan,
		payment_method=payment_method,
		amount_vnd=amount_vnd,
		qr_available=bool(qrcode),
	)


@predict_bp.route("/payment/qr.png", methods=["GET"])
def payment_qr_png():
	"""Trả về ảnh QR PNG cho đơn hàng pending trong session (demo)."""
	user_id = _get_session_user_id()
	if user_id is None:
		return ("Unauthorized", 401)
	if qrcode is None:
		return ("QR generator missing. Install 'qrcode' package.", 500)

	pending = session.get("pending_payment") or {}
	order_id = pending.get("order_id")
	if not order_id:
		return ("No pending order", 404)

	conn = None
	try:
		conn = get_connection()
		order = PaymentOrder.get_by_order_id(conn, order_id)
	finally:
		if conn:
			conn.close()

	order_user_id = None
	if order is not None:
		raw_user_id = order.get("user_id")
		if raw_user_id is not None:
			try:
				order_user_id = int(raw_user_id)
			except (TypeError, ValueError):
				order_user_id = None
	if not order or order_user_id != user_id:
		return ("Order not found", 404)

	plan = order.get("plan")
	method = order.get("payment_method")
	amount = order.get("amount_vnd")

	# VietQR payload chuẩn (EMVCo). Nếu chưa cấu hình ngân hàng thì fallback demo.
	bank_bin = (current_app.config.get("VIETQR_BANK_BIN") or "").strip()
	bank_account = (current_app.config.get("VIETQR_ACCOUNT_NUMBER") or "").strip()
	bank_name = (current_app.config.get("VIETQR_BANK_NAME") or "").strip()
	account_name = (current_app.config.get("VIETQR_ACCOUNT_NAME") or "").strip()
	merchant_city = (current_app.config.get("VIETQR_MERCHANT_CITY") or "HANOI").strip()
	merchant_name = (current_app.config.get("VIETQR_MERCHANT_NAME") or account_name or "DOG AI APP").strip()

	try:
		if bank_bin and bank_account:
			payload = build_vietqr_payload(
				bank_bin=bank_bin,
				account_number=bank_account,
				amount_vnd=int(amount or 0),
				order_id=str(order_id),
				account_name=account_name,
				merchant_name=merchant_name,
				merchant_city=merchant_city,
			)
		else:
			payload = f"DOGAI_PAY|ORDER={order_id}|PLAN={plan}|METHOD={method}|AMOUNT_VND={amount}|USER={session.get('username','user')}"
	except Exception:
		payload = f"DOGAI_PAY|ORDER={order_id}|PLAN={plan}|METHOD={method}|AMOUNT_VND={amount}|USER={session.get('username','user')}"
	img = qrcode.make(payload)
	buf = BytesIO()
	img.save(buf, "PNG")
	buf.seek(0)
	return send_file(buf, mimetype="image/png")


@predict_bp.route("/upgrade/buy", methods=["POST"])
def upgrade_buy():
	"""Demo: nâng gói theo lựa chọn để tiếp tục sử dụng."""
	user_id = _get_session_user_id()
	if user_id is None:
		flash("Vui lòng đăng nhập để sử dụng chức năng này.", "warning")
		return redirect(url_for("login.login"))

	# Nếu đi qua trang checkout, bắt buộc khớp order_id trong session
	posted_order_id = (request.form.get("order_id") or "").strip()
	pending = session.get("pending_payment")
	if pending:
		if posted_order_id != (pending.get("order_id") or ""):
			flash("Đơn thanh toán không hợp lệ hoặc đã hết hạn. Vui lòng thử lại.", "error")
			return redirect(url_for("predict.upgrade"))
		order_id = pending.get("order_id")
	else:
		plan = (request.form.get("plan") or "pro").strip().lower()
		payment_method = (request.form.get("payment_method") or "qr").strip().lower()
		order_id = ""

	allowed_plans = {"basic", "pro", "enterprise"}
	allowed_payments = {"qr", "momo", "vnpay", "bank", "card"}
	if plan not in allowed_plans:
		plan = "pro"
	if payment_method not in allowed_payments:
		payment_method = "qr"

	conn = None
	try:
		conn = get_connection()
		if pending:
			order = PaymentOrder.get_by_order_id(conn, order_id)
			order_user_id = None
			if order is not None:
				raw_user_id = order.get("user_id")
				if raw_user_id is not None:
					try:
						order_user_id = int(raw_user_id)
					except (TypeError, ValueError):
						order_user_id = None
			if not order or order_user_id != user_id:
				flash("Đơn thanh toán không tồn tại hoặc không hợp lệ.", "error")
				return redirect(url_for("predict.upgrade"))
			plan = (order.get("plan") or "pro").strip().lower()
			payment_method = (order.get("payment_method") or "qr").strip().lower()
		# Demo mapping: basic/pro/enterprise đều không bị chặn bởi ads nữa.
		# (Nếu bạn muốn hạn mức theo tháng cho basic, mình sẽ thêm counter theo tháng.)
		UserQuota.set_plan(conn, user_id, plan)
		if pending:
			PaymentOrder.mark_paid(conn, order_id)
		# Clear pending payment
		try:
			session.pop("pending_payment", None)
		except Exception:
			pass
		flash(f"Thanh toán (demo) thành công qua {payment_method.upper()}. Đã kích hoạt gói {str(plan).upper()}.", "success")
		return redirect(url_for("predict.upload_page"))
	except Exception as e:
		print("[UPGRADE] buy error:", e)
		flash("Không thể nâng cấp gói. Vui lòng thử lại.", "error")
		return redirect(url_for("predict.upgrade"))
	finally:
		if conn:
			conn.close()


@predict_bp.route("/payments", methods=["GET"])
def my_payments():
	user_id = _get_session_user_id()
	if user_id is None:
		flash("Vui lòng đăng nhập để xem lịch sử thanh toán.", "warning")
		return redirect(url_for("login.login"))

	conn = None
	try:
		conn = get_connection()
		orders = PaymentOrder.list_by_user(conn, user_id, limit=50)
	finally:
		if conn:
			conn.close()

	return render_template("payments_user.html", orders=orders)


def allowed_file(filename: str) -> bool:
	allowed = current_app.config.get("ALLOWED_EXTENSIONS", {"png", "jpg", "jpeg"})
	return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


@predict_bp.route("/upload", methods=["POST"])
def upload():
	# Bắt buộc đăng nhập mới được sử dụng chức năng này
	user_id = _get_session_user_id()
	if user_id is None:
		flash("Vui lòng đăng nhập để sử dụng chức năng này.", "warning")
		return redirect(url_for("login.login"))

	if "image" not in request.files:
		flash("Không tìm thấy file ảnh.", "error")
		return redirect(url_for("home.index"))
	file = request.files.get("image")
	fname = (file.filename if file is not None else None) or ""
	if fname == "":
		flash("Tên file không hợp lệ.", "error")
		return redirect(url_for("home.index"))
	if file and allowed_file(fname):
		filename = secure_filename(fname)
		upload_dir = current_app.config.get("UPLOAD_FOLDER")
		if not upload_dir:
			upload_dir = os.path.join("static", "uploads")
			os.makedirs(upload_dir, exist_ok=True)
		save_path = os.path.join(upload_dir, filename)

		# --- Quota gate (only for role=user) ---
		try:
			role = session.get("role", "user")
			if role == "user":
				conn_q = get_connection()
				try:
					quota = UserQuota.get_or_create(conn_q, user_id)
					# Gói trả phí: bỏ qua giới hạn/ads
					if quota.get("plan") == "free":
						total_predictions = PredictionHistory.count_by_user(conn_q, user_id)
						if int(total_predictions or 0) >= UserQuota.FREE_PREDICTIONS:
							# hết free -> cần unlock từ quảng cáo
							if int(quota.get("ad_unlocks_remaining", 0)) <= 0:
								if int(quota.get("ad_views_used", 0)) >= UserQuota.MAX_AD_VIEWS:
									flash("Bạn đã dùng hết 10 lượt miễn phí và 3 lượt xem quảng cáo. Vui lòng mua gói để tiếp tục.", "warning")
									return redirect(url_for("predict.upgrade"))
								flash("Bạn đã dùng hết 10 lượt miễn phí. Vui lòng xem quảng cáo để mở khóa thêm.", "info")
								return redirect(url_for("predict.watch_ad"))
							# Consume 1 unlock cho lần nhận diện này
							if not UserQuota.consume_ad_unlock(conn_q, user_id):
								flash("Vui lòng xem quảng cáo để mở khóa thêm lượt nhận diện.", "info")
								return redirect(url_for("predict.watch_ad"))
				finally:
					conn_q.close()
		except Exception as e:
			print("[QUOTA] gate error:", e)

		file.save(save_path)


		# --- YOLOv8 inference ---
		# Lưu ý: mô hình detect (yolov8n.pt) không có probs.top1 như mô hình classify.
		# Thay vào đó dùng boxes.cls để lấy class id, map sang tên và chọn 'dog' hoặc 'cat' nếu có.
		try:
			det_results = det_model(save_path)
			r = det_results[0]
			names = getattr(r, 'names', {}) or {}
			det_label = 'Unknown'
			det_items = []
			if hasattr(r, 'boxes') and r.boxes is not None and getattr(r.boxes, 'cls', None) is not None:
				cls_list = r.boxes.cls.tolist()
				# Trường hợp chỉ 1 phần tử có thể là float -> chuyển về list
				if not isinstance(cls_list, list):
					cls_list = [cls_list]
				labels = []
				for ci in cls_list:
					try:
						labels.append(names[int(ci)])
					except Exception:
						continue
				# Lấy conf và bbox nếu có để hiển thị chi tiết
				confs = r.boxes.conf.tolist() if getattr(r.boxes, 'conf', None) is not None else [None] * len(labels)
				xyxy = r.boxes.xyxy.tolist() if getattr(r.boxes, 'xyxy', None) is not None else [None] * len(labels)
				for lab, cf, bb in zip(labels, confs, xyxy):
					item = {
						'label': lab,
						'conf': float(cf) if cf is not None else None,
						'bbox': bb,
					}
					det_items.append(item)
				# Ưu tiên theo box có độ tự tin cao nhất giữa dog/cat
				best_species = None
				best_conf = -1.0
				if hasattr(r.boxes, 'conf') and r.boxes.conf is not None:
					confs = r.boxes.conf.tolist()
					for lab, conf in zip(labels, confs):
						if lab in ('dog', 'cat') and conf > best_conf:
							best_species = lab
							best_conf = conf
				# Nếu không có conf thì chỉ cần thấy có dog/cat là chọn
				if best_species is None:
					if 'dog' in labels:
						best_species = 'dog'
					elif 'cat' in labels:
						best_species = 'cat'
				if best_species is not None:
					det_label = 'Dog' if best_species == 'dog' else 'Cat'

			# Vẽ bbox lên ảnh (chỉ cho dog/cat) nếu có bbox
			annotated_path = save_path
			try:
				if det_items:
					img = cv2.imread(save_path)
					for it in det_items:
						bb = it.get('bbox')
						lab = it.get('label')
						if not bb or lab not in ('dog', 'cat'):
							continue
						x1, y1, x2, y2 = [int(v) for v in bb]
						color = (255, 128, 0) if lab == 'dog' else (0, 165, 255)  # BGR: dog=blue-ish, cat=orange
						cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
						conf_txt = f"{int(round((it.get('conf') or 0)*100))}%"
						label_txt = f"{lab.upper()} {conf_txt if it.get('conf') is not None else ''}"
						# Draw label background
						(tw, th), _ = cv2.getTextSize(label_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
						cv2.rectangle(img, (x1, max(y1- th - 6, 0)), (x1 + tw + 6, y1), color, -1)
						cv2.putText(img, label_txt, (x1+3, y1-6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2, cv2.LINE_AA)
					# Lưu ảnh annotate cạnh file gốc
					base, ext = os.path.splitext(save_path)
					annotated_path = f"{base}_det{ext}"
					cv2.imwrite(annotated_path, img)
			except Exception as _:
				annotated_path = save_path

		except Exception as e:
			print("YOLO detect error:", e)
			det_label = 'Unknown'
			det_items = []
			annotated_path = save_path

		try:
			seg_results = seg_model(save_path)
			seg_masks = seg_results[0].masks.data.cpu().numpy() if hasattr(seg_results[0], 'masks') and seg_results[0].masks is not None else None
		except Exception as e:
			print("YOLO seg error:", e)
			seg_masks = None

		# Kết quả cũ (HOG+SVM)
		result = predictor.predict(save_path)

		# Tìm confidence của loài YOLOv8 (dog/cat) để hiển thị
		yolo_conf = None
		if det_label in ["Dog", "Cat"] and det_items:
			for item in det_items:
				if (det_label == "Dog" and item["label"] == "dog") or (det_label == "Cat" and item["label"] == "cat"):
					yolo_conf = item["conf"]
					break

		# Gate: chỉ khi xác nhận là chó >= 75% mới bắt đầu suy luận giống
		DOG_THRESHOLD = 0.75
		is_dog_enough = (det_label == "Dog") and (yolo_conf is not None) and (float(yolo_conf) >= DOG_THRESHOLD)
		if not is_dog_enough:
			# Không phải chó / hoặc độ tin cậy thấp -> không suy luận giống
			note = None
			if det_label != "Dog":
				note = "Ảnh này không được nhận diện là CHÓ. Vui lòng tải ảnh có chó rõ ràng để nhận diện giống."
			else:
				pct = int(round(float(yolo_conf or 0) * 100))
				note = f"Độ tin cậy CHÓ chỉ {pct}% (< 75%). Vui lòng tải ảnh rõ hơn để nhận diện giống."
			flash(note, "warning")
			return render_template(
				"predict.html",
				image_path=annotated_path.replace("\\", "/"),
				result={"breed": "Không xác định", "breed_conf": 0.0, "note": note},
				yolo_species=det_label,
				yolo_species_conf=yolo_conf,
				yolo_detections=det_items,
				yolo_masks=seg_masks,
			)

		# Nếu có YOLO breed model, suy luận giống từ đó và ghi đè result.breed
		if breed_model is not None:
			try:
				br = breed_model(save_path)[0]
				breed_name = None
				breed_conf = None
				if hasattr(br, 'boxes') and br.boxes is not None:
					names = getattr(br, 'names', {}) or {}
					# lấy box có conf cao nhất
					confs = br.boxes.conf.tolist() if getattr(br.boxes, 'conf', None) is not None else []
					cls = br.boxes.cls.tolist() if getattr(br.boxes, 'cls', None) is not None else []
					if confs and cls and len(confs) == len(cls):
						best_i = max(range(len(confs)), key=lambda i: confs[i])
						breed_name = names.get(int(cls[best_i]), None)
						breed_conf = confs[best_i]
				if breed_name:
					# override breed in result
					if isinstance(result, dict):
						result['breed'] = breed_name
						result['breed_conf'] = breed_conf
			except Exception as _:
				pass
		
		# Lưu vào database (chỉ khi đã pass gate chó >= 75%)
		try:
			if user_id is not None:
				conn = get_connection()
				breed_to_save = result.get('breed', 'Unknown') if isinstance(result, dict) else 'Unknown'
				conf_to_save = result.get('breed_conf', 0.0) if isinstance(result, dict) else 0.0
				PredictionHistory.save(
					conn, 
					user_id,
					annotated_path.replace("\\", "/"),
					breed_to_save,
					float(conf_to_save) if conf_to_save else 0.0,
					det_label
				)
				conn.close()
		except Exception as e:
			print(f"Warning: Could not save to history: {e}")
		
		return render_template(
			"predict.html",
			image_path=annotated_path.replace("\\", "/"),
			result=result,
			yolo_species=det_label,
			yolo_species_conf=yolo_conf,
			yolo_detections=det_items,
			yolo_masks=seg_masks,
		)

	flash("Định dạng file không được hỗ trợ.", "error")
	return redirect(url_for("home.index"))
