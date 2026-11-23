from django.conf import settings
from django.utils import timezone
from fpdf import FPDF
from fpdf.fonts import FontFace


CHART_COLORS = {
    'weekly': (34, 97, 154),
    'status': (8, 120, 91),
    'overdue': (179, 91, 25),
}
CHART_TRACK = (229, 235, 239)


def draw_chart(pdf, chart):
    rows = chart['rows']
    weekly = chart['variant'] == 'weekly'
    height = 60 if weekly and rows else 20 + 11 * len(rows)
    if pdf.will_page_break(height):
        pdf.add_page()

    pdf.ln(4)
    pdf.set_font('Tajawal', 'B', 14)
    pdf.cell(w=pdf.epw, h=7, text=chart['title'], align='R', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Tajawal', size=10)
    pdf.cell(w=pdf.epw, h=5, text=chart['caption'], align='R', new_x='LMARGIN', new_y='NEXT')
    if not rows:
        pdf.cell(w=pdf.epw, h=6, text='لا توجد بيانات لعرضها.', align='R', new_x='LMARGIN', new_y='NEXT')
        return

    accent = CHART_COLORS[chart['variant']]
    if weekly:
        draw_weekly_chart(pdf, rows, accent)
        return

    count_width = 16
    track_width = pdf.epw - count_width
    right = pdf.w - pdf.r_margin
    for row in rows:
        if pdf.will_page_break(18):
            pdf.add_page()
        pdf.multi_cell(w=pdf.epw, h=5, text=row['label'], align='R', new_x='LMARGIN', new_y='NEXT')
        y = pdf.get_y()
        pdf.set_fill_color(*CHART_TRACK)
        pdf.rect(right - track_width, y + 1, track_width, 2.5, style='F')
        bar_width = track_width * row['count'] / row['max']
        if bar_width:
            pdf.set_fill_color(*accent)
            pdf.rect(right - bar_width, y + 1, bar_width, 2.5, style='F')
        pdf.cell(w=count_width, h=5, text=str(row['count']), align='L', new_x='LMARGIN', new_y='NEXT')
        pdf.ln(1)


def draw_weekly_chart(pdf, rows, accent):
    column_width = pdf.epw / len(rows)
    track_height = 28
    top = pdf.get_y() + 7
    right = pdf.w - pdf.r_margin
    for index, row in enumerate(rows):
        x = right - (index + 1) * column_width
        track_width = column_width * 0.6
        bar_x = x + (column_width - track_width) / 2
        pdf.set_fill_color(*CHART_TRACK)
        pdf.rect(bar_x, top, track_width, track_height, style='F')
        bar_height = track_height * row['count'] / row['max']
        if bar_height:
            pdf.set_fill_color(*accent)
            pdf.rect(bar_x, top + track_height - bar_height, track_width, bar_height, style='F')
        pdf.set_xy(x, top - 6)
        pdf.cell(w=column_width, h=5, text=str(row['count']), align='C')
        pdf.set_xy(x, top + track_height + 1)
        pdf.cell(w=column_width, h=5, text=row['label'], align='C')
    pdf.set_xy(pdf.l_margin, top + track_height + 7)


def report_pdf(context):
    pdf = FPDF()
    pdf.set_title(context['title'])
    fonts = settings.BASE_DIR / 'core' / 'static' / 'core' / 'fonts'
    pdf.add_font('Tajawal', fname=fonts / 'tajawal-regular.ttf')
    pdf.add_font('Tajawal', style='B', fname=fonts / 'tajawal-bold.ttf')
    pdf.set_text_shaping(True)
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    pdf.set_font('Tajawal', 'B', 20)
    pdf.cell(w=pdf.epw, h=10, text=context['title'], align='R', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Tajawal', size=11)
    generated = timezone.localtime(context['generated_at']).strftime('%Y/%m/%d %H:%M')
    pdf.cell(w=pdf.epw, h=6, text=f'تاريخ التوليد: \u2066{generated}\u2069', align='R', new_x='LMARGIN', new_y='NEXT')

    def section(title, headings, rows, widths, empty='لا توجد بيانات.'):
        if pdf.will_page_break(40):
            pdf.add_page()
        pdf.ln(4)
        pdf.set_font('Tajawal', 'B', 14)
        pdf.cell(w=pdf.epw, h=7, text=title, align='R', new_x='LMARGIN', new_y='NEXT')
        pdf.set_font('Tajawal', size=11)
        rows = list(rows)
        if not rows:
            pdf.cell(w=pdf.epw, h=6, text=empty, align='R', new_x='LMARGIN', new_y='NEXT')
            return
        with pdf.table(
            col_widths=tuple(reversed(widths)),
            headings_style=FontFace(emphasis='BOLD', fill_color=(225, 240, 234)),
            line_height=6, padding=2, text_align='RIGHT', borders_layout='HORIZONTAL_LINES',
        ) as table:
            table.row(tuple(reversed(headings)))
            for row in rows:
                table.row(tuple(str(value) for value in reversed(row)))

    section('المؤشرات العامة', ('المؤشر', 'القيمة'), [
        ('إجمالي الشكاوى', context['total_complaints']),
        ('الشكاوى المفتوحة', context['open_complaints']),
        ('نسبة الشكاوى المعالجة', f"{context['completion_rate']}٪"),
        ('إجمالي الإحالات', context['total_assignments']),
        ('الإحالات المتأخرة', context['overdue_count']),
        ('تنبيهاتك غير المقروءة', context['unread_notifications']),
    ], (3, 1))
    for chart in context['report_charts']:
        draw_chart(pdf, chart)

    section('الشكاوى حسب الحالة', ('الحالة', 'العدد', 'النسبة'),
            ((row['label'], row['count'], f"{row['percent']}٪") for row in context['complaint_rows']), (3, 1, 1))
    section('حالات الإحالات', ('الحالة', 'العدد'),
            ((row['label'], row['count']) for row in context['assignment_rows']), (3, 1), 'لا توجد إحالات مسجلة بعد.')
    section('متابعة الأقسام', ('القسم', 'الإحالات', 'المعتمدة', 'المتأخرة'),
            ((row.name, row.total, row.approved, row.overdue) for row in context['departments']),
            (3, 1, 1, 1), 'لا توجد أقسام مسجلة.')

    overdue_rows = []
    for item in context['overdue_assignments']:
        officer = (item.officer.get_full_name() or item.officer.username) if item.officer else 'غير مسندة لموظف'
        overdue_rows.append((
            item.complaint.reference, item.complaint.title, f'{item.department.name}\n{officer}',
            timezone.localtime(item.due_at).strftime('%Y/%m/%d %H:%M'),
        ))
    section('الإحالات المتأخرة — أقدم 20 إحالة', ('الرقم المرجعي', 'الشكوى', 'القسم المختص', 'الموعد المحدد'),
            overdue_rows, (2, 3, 3, 2), 'لا توجد إحالات متأخرة حالياً.')
    return bytes(pdf.output())
