from __future__ import annotations

import re
from typing import Optional


def _only_ascii(text: str, max_len: int) -> str:
	"""EMV/VietQR thường hoạt động ổn nhất với ASCII.
	Giữ lại A-Z0-9 và khoảng trắng cơ bản, cắt độ dài để tránh app ngân hàng từ chối.
	"""
	text = (text or "").strip()
	# thay ký tự không ASCII bằng khoảng trắng
	text = text.encode("ascii", errors="ignore").decode("ascii")
	text = re.sub(r"\s+", " ", text).strip()
	if max_len > 0:
		text = text[:max_len]
	return text


def _tlv(tag: str, value: str) -> str:
	"""Build EMV TLV: TAG(2) + LEN(2) + VALUE.
	LEN tính theo số ký tự (ASCII) của VALUE.
	"""
	if value is None:
		value = ""
	length = len(value)
	return f"{tag}{length:02d}{value}"


def _crc16_ccitt_false(data: bytes) -> int:
	"""CRC16-CCITT-FALSE: poly 0x1021, init 0xFFFF, xorout 0x0000."""
	crc = 0xFFFF
	for b in data:
		crc ^= (b << 8)
		for _ in range(8):
			if crc & 0x8000:
				crc = ((crc << 1) ^ 0x1021) & 0xFFFF
			else:
				crc = (crc << 1) & 0xFFFF
	return crc & 0xFFFF


def build_vietqr_payload(
	*,
	bank_bin: str,
	account_number: str,
	amount_vnd: int = 0,
	order_id: Optional[str] = None,
	account_name: str = "",
	merchant_name: str = "DOG AI APP",
	merchant_city: str = "HANOI",
	service_code: str = "QRIBFTTA",
) -> str:
	"""Build VietQR payload (EMVCo Merchant Presented Mode).

	- bank_bin: BIN 6 số (VD: 970436)
	- account_number: số tài khoản nhận
	- amount_vnd: số tiền (VND)
	- order_id: nhúng vào Additional Data (tag 62)
	- service_code: QRIBFTTA (to account) / QRIBFTTC (to card)

	Lưu ý: Đây là payload string; phía ngoài sẽ encode thành QR.
	"""
	bank_bin = (bank_bin or "").strip()
	account_number = (account_number or "").strip()
	if not bank_bin.isdigit() or len(bank_bin) != 6:
		raise ValueError("bank_bin must be 6 digits")
	if not account_number:
		raise ValueError("account_number is required")

	merchant_name = _only_ascii(merchant_name, 25) or "DOG AI APP"
	merchant_city = _only_ascii(merchant_city, 15) or "HANOI"

	# 00: Payload Format Indicator
	parts = [_tlv("00", "01")]

	# 01: Point of Initiation Method
	# 11: static, 12: dynamic
	poi = "12" if int(amount_vnd or 0) > 0 else "11"
	parts.append(_tlv("01", poi))

	# 38: Merchant Account Information (VietQR / NAPAS)
	#  - 00: GUID (A000000727)
	#  - 01: Beneficiary info
	#       - 00: bank BIN
	#       - 01: account number
	#       - 02: service code (QRIBFTTA)
	mai_guid = _tlv("00", "A000000727")
	benef = _tlv("00", bank_bin) + _tlv("01", account_number) + _tlv("02", service_code)
	mai_benef = _tlv("01", benef)
	parts.append(_tlv("38", mai_guid + mai_benef))

	# 52: Merchant Category Code (0000)
	parts.append(_tlv("52", "0000"))
	# 53: Transaction Currency (704 = VND)
	parts.append(_tlv("53", "704"))
	# 54: Amount (optional)
	if int(amount_vnd or 0) > 0:
		parts.append(_tlv("54", str(int(amount_vnd))))
	# 58: Country Code
	parts.append(_tlv("58", "VN"))
	# 59: Merchant Name
	parts.append(_tlv("59", merchant_name))
	# 60: Merchant City
	parts.append(_tlv("60", merchant_city))

	# 62: Additional Data Field Template
	addl = ""
	if order_id:
		addl += _tlv("01", _only_ascii(str(order_id), 25))
	# purpose / reference: thường app ngân hàng sẽ hiển thị/điền nội dung chuyển khoản
	purpose = _only_ascii(f"DOGAI {order_id}" if order_id else "DOGAI", 25)
	addl += _tlv("08", purpose)
	if addl:
		parts.append(_tlv("62", addl))

	payload_no_crc = "".join(parts) + "6304"
	crc = _crc16_ccitt_false(payload_no_crc.encode("ascii"))
	return payload_no_crc + f"{crc:04X}"
