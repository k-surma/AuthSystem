from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime, timedelta
from typing import List
import os

class ReportService:
    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = reports_dir
        os.makedirs(reports_dir, exist_ok=True)
    
    @staticmethod
    def _strip_pl_accents(text: str) -> str:
        if not isinstance(text, str):
            return text
        mapping = str.maketrans(
            "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ",
            "acelnoszzACELNOSZZ",
        )
        return text.translate(mapping)

    def generate_access_report(self, logs: List[dict], start_date: datetime = None, end_date: datetime = None) -> str:
        if start_date is None:
            start_date = datetime.now() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now()
        
        filename = f"access_report_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"
        filepath = os.path.join(self.reports_dir, filename)
        
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        elements = []
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
        )
        
        title_text = "Raport Dostepu - System Weryfikacji Tozsamosci"
        title = Paragraph(title_text, title_style)
        elements.append(title)
        
        period_text = f"Okres: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}"
        period_text = self._strip_pl_accents(period_text)
        period = Paragraph(period_text, styles['Normal'])
        elements.append(period)
        elements.append(Spacer(1, 0.2*inch))
        
        total_logs = len(logs)
        accepted = sum(1 for log in logs if log.get('result') == 'ACCEPT')
        rejected = sum(1 for log in logs if log.get('result') == 'REJECT')
        suspicious = sum(1 for log in logs if log.get('result') == 'SUSPICIOUS')
        
        stats_data = [
            [self._strip_pl_accents('Statystyki'), ''],
            [self._strip_pl_accents('Laczna liczba zdarzen'), str(total_logs)],
            [self._strip_pl_accents('Zaakceptowane'), str(accepted)],
            [self._strip_pl_accents('Odrzucone'), str(rejected)],
            [self._strip_pl_accents('Podejrzane'), str(suspicious)],
        ]
        
        stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 0.3*inch))
        
        if logs:
            table_data = [['Data/Czas', 'Wynik', 'Score', 'User ID', 'Badge ID']]
            
            for log in logs[:100]:
                timestamp = log.get('timestamp', '')
                if isinstance(timestamp, datetime):
                    timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                
                table_data.append([
                    str(timestamp),
                    self._strip_pl_accents(log.get('result', '')),
                    f"{log.get('match_score'):.2f}" if log.get('match_score') is not None else '-',
                    str(log.get('user_id', '-')),
                    str(log.get('badge_id', '-'))
                ])
            
            table = Table(table_data, colWidths=[1.5*inch, 1*inch, 0.8*inch, 0.8*inch, 0.8*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
            ]))
            elements.append(table)

            failed_logs = [
                log for log in logs
                if log.get('result') in ('REJECT', 'SUSPICIOUS')
                and log.get('image_path')
            ]

            if failed_logs:
                elements.append(Spacer(1, 0.4 * inch))
                failed_title_text = "Nieudane proby dostepu (REJECT / SUSPICIOUS) ze zdjeciami"
                failed_title = Paragraph(
                    failed_title_text,
                    styles['Heading2'],
                )
                elements.append(failed_title)
                elements.append(Spacer(1, 0.2 * inch))

                for log in failed_logs:
                    img_path = log.get('image_path')
                    img_loaded = False
                    if img_path:
                        try:
                            img = RLImage(img_path, width=2.0 * inch, height=2.0 * inch)
                            elements.append(img)
                            img_loaded = True
                        except Exception:
                            info_text = f"Nie udalo sie wczytac obrazu: {img_path}"
                            info = Paragraph(info_text, styles['Italic'])
                            elements.append(info)

                    ts = log.get('timestamp')
                    if isinstance(ts, datetime):
                        ts_str = ts.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        ts_str = str(ts)

                    caption_text = (
                        f"Data/Czas: {ts_str}<br/>"
                        f"Wynik: {self._strip_pl_accents(log.get('result', ''))}<br/>"
                        f"Score: {log.get('match_score', '-') if log.get('match_score') is not None else '-'}<br/>"
                        f"User ID: {log.get('user_id', '-')}, "
                        f"Badge ID: {log.get('badge_id', '-')}<br/>"
                        f"Sciezka obrazu: {img_path or '-'}"
                    )
                    caption = Paragraph(caption_text, styles['Normal'])
                    elements.append(caption)
                    elements.append(Spacer(1, 0.2 * inch))
        else:
            no_data = Paragraph("Brak danych w wybranym okresie", styles['Normal'])
            elements.append(no_data)
        
        doc.build(elements)
        return filepath




