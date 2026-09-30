"""Digital Pass PDF Generator for Evangelism Events.

Generates official carnet / boarding pass PDFs with ReportLab and embedded QR codes.
Follows CCF Design System principles and produces printable/mobile-ready passes.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Optional

import qrcode
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from backend import models


def generate_event_pass_pdf(
    event: models.CrmEvent,
    reg: models.EventRegistration,
    persona: Optional[models.Persona],
    *,
    base_url: str = "https://ccf.co",
) -> bytes:
    """Genera un archivo PDF con el Pase Digital de acceso al evento."""
    buf = io.BytesIO()

    # Dimensiones estilo carnet / boarding pass (120mm x 185mm)
    page_width = 125 * mm
    page_height = 190 * mm
    doc = SimpleDocTemplate(
        buf,
        pagesize=(page_width, page_height),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )

    styles = getSampleStyleSheet()

    # Estilos tipográficos
    title_style = ParagraphStyle(
        "PassTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#0F172A"),
        alignment=1,  # Centered
    )

    header_sub_style = ParagraphStyle(
        "PassHeaderSub",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#475569"),
        alignment=1,
    )

    reg_num_style = ParagraphStyle(
        "PassRegNum",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=14,
        textColor=colors.HexColor("#1D4ED8"),
        alignment=1,
    )

    name_style = ParagraphStyle(
        "PassName",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1E293B"),
        alignment=1,
    )

    meta_label_style = ParagraphStyle(
        "PassMetaLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#64748B"),
    )

    meta_val_style = ParagraphStyle(
        "PassMetaVal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0F172A"),
    )

    footer_style = ParagraphStyle(
        "PassFooter",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.5,
        leading=8,
        textColor=colors.HexColor("#94A3B8"),
        alignment=1,
    )

    story = []

    # 1. Cabecera Institucional
    header_data = [
        [Paragraph("CENTRO CRISTIANO DE FE", header_sub_style)],
        [Paragraph("PASE DIGITAL DE ACCESO", ParagraphStyle("H1", parent=header_sub_style, fontSize=7, textColor=colors.HexColor("#2563EB")))],
    ]
    header_table = Table(header_data, colWidths=[page_width - 20 * mm])
    header_table.setStyle(
        TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(header_table)
    story.append(Spacer(1, 4 * mm))

    # 2. Nombre del Evento
    story.append(Paragraph(event.name or "Evento CCF", title_style))
    story.append(Spacer(1, 2 * mm))

    # 3. Número de Registro Correlativo
    reg_num = getattr(reg, "registration_number", None) or 1
    reg_code = f"#CCF-EVT-{reg_num:04d}"
    code_data = [[Paragraph(f"<b>{reg_code}</b>", reg_num_style)]]
    code_table = Table(code_data, colWidths=[page_width - 20 * mm])
    code_table.setStyle(
        TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#BFDBFE")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(code_table)
    story.append(Spacer(1, 3 * mm))

    # 4. Nombre del Asistente
    attendee_name = (persona.nombre_completo if persona else None) or "Participante Registrado"
    story.append(Paragraph(attendee_name, name_style))
    story.append(Spacer(1, 3 * mm))

    # 5. Código QR Interactivo
    # TKT-EVT-AUDIT-QR-PREINSCRIPCION-01: el token plano nunca se persiste en DB
    # (qr_token queda NULL), así que el pase NO puede codificar un token que no
    # existe. El QR codifica la URL del ticket público resoluble por ``reg.id``
    # (UUIDv4 no adivinable) cuando no hay token; con token persistido se mantiene
    # el formato hash-bound canónico. El check-in extrae ``token=`` de la URL
    # escaneada (interop escáner) y resuelve la inscripción de forma segura.
    if reg.qr_token:
        qr_token_value = reg.qr_token
    else:
        qr_token_value = str(reg.id)
    qr_payload = f"{base_url}/public/events/{event.id}/qr?token={qr_token_value}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=1,
    )
    qr.add_data(qr_payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0F172A", back_color="white")
    img_buf = io.BytesIO()
    img.save(img_buf, format="PNG")
    img_buf.seek(0)
    qr_flowable = Image(img_buf, width=38 * mm, height=38 * mm)
    qr_flowable.hAlign = "CENTER"
    story.append(qr_flowable)
    story.append(Spacer(1, 3 * mm))

    # 6. Tabla de Metadatos (Fecha, Hora, Lugar, Estado)
    event_date_str = ""
    if event.event_date:
        event_date_str = event.event_date.strftime("%d/%m/%Y")
    elif event.fixed_date:
        event_date_str = event.fixed_date.strftime("%d/%m/%Y")
    time_str = event.start_time or "Por confirmar"
    location_str = event.location or "Sede Central CCF"
    status_str = "CONFIRMADO" if reg.registration_status in {"CONFIRMED", "CHECKED_IN"} else reg.registration_status

    meta_rows = [
        [
            Paragraph("FECHA:", meta_label_style),
            Paragraph(f"<b>{event_date_str or 'Pendiente'}</b>", meta_val_style),
            Paragraph("HORA:", meta_label_style),
            Paragraph(f"<b>{time_str}</b>", meta_val_style),
        ],
        [
            Paragraph("LUGAR:", meta_label_style),
            Paragraph(location_str, meta_val_style),
            Paragraph("ESTADO:", meta_label_style),
            Paragraph(f"<font color='#16A34A'><b>{status_str}</b></font>", meta_val_style),
        ],
    ]
    meta_table = Table(
        meta_rows,
        colWidths=[15 * mm, 38 * mm, 15 * mm, 37 * mm],
    )
    meta_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#F1F5F9")),
        ])
    )
    story.append(meta_table)
    story.append(Spacer(1, 4 * mm))

    # 7. Línea divisoria y Footer
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceAfter=3))
    now_utc = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    story.append(
        Paragraph(
            f"Presenta este pase digital o impreso en la entrada del auditorio.<br/>"
            f"Generado el {now_utc} • Plataforma Canónica CCF",
            footer_style,
        )
    )

    doc.build(story)
    return buf.getvalue()
