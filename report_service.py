from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime, timedelta
from typing import List
import os

class ReportService:
    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = reports_dir
        os.makedirs(reports_dir, exist_ok=True)
    
    def generate_access_report(self, logs: List[dict], start_date: datetime = None, end_date: datetime = None) -> str:
        """
        Generuje raport PDF z logami dostępu
        Zwraca ścieżkę do wygenerowanego pliku
        """
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
        
        # Tytuł
        title = Paragraph("Raport Dostępu - System Weryfikacji Tożsamości", title_style)
        elements.append(title)
        
        # Informacje o okresie
        period_text = f"Okres: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}"
        period = Paragraph(period_text, styles['Normal'])
        elements.append(period)
        elements.append(Spacer(1, 0.2*inch))
        
        # Statystyki
        total_logs = len(logs)
        accepted = sum(1 for log in logs if log.get('result') == 'ACCEPT')
        rejected = sum(1 for log in logs if log.get('result') == 'REJECT')
        suspicious = sum(1 for log in logs if log.get('result') == 'SUSPICIOUS')
        
        stats_data = [
            ['Statystyki', ''],
            ['Łączna liczba zdarzeń', str(total_logs)],
            ['Zaakceptowane', str(accepted)],
            ['Odrzucone', str(rejected)],
            ['Podejrzane', str(suspicious)],
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
        
        # Tabela logów
        if logs:
            table_data = [['Data/Czas', 'Wynik', 'Score', 'User ID', 'Badge ID']]
            
            for log in logs[:100]:  # Ograniczenie do 100 wierszy
                timestamp = log.get('timestamp', '')
                if isinstance(timestamp, datetime):
                    timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                
                table_data.append([
                    str(timestamp),
                    log.get('result', ''),
                    f"{log.get('match_score', 0):.2f}" if log.get('match_score') else '-',
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
        else:
            no_data = Paragraph("Brak danych w wybranym okresie", styles['Normal'])
            elements.append(no_data)
        
        # Generuj PDF
        doc.build(elements)
        return filepath


