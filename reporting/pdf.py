import logging

from django.conf import settings
from django.utils import timezone
from fpdf import FPDF
from fpdf.fonts import FontFace
from PIL import Image


logger = logging.getLogger(__name__)
REPORT_INK = (29, 48, 45)
REPORT_RULE = (211, 225, 220)
REPORT_HEADER = (237, 245, 241)


CHART_COLORS = {
    'weekly': (34, 97, 154),
    'status': (8, 120, 91),
    'assignment': (85, 70, 148),
    'overdue': (179, 91, 25),
}
CHART_TRACK = (229, 235, 239)
DEPARTMENT_COLORS = {
    'total': CHART_COLORS['weekly'],
    'approved': CHART_COLORS['status'],
    'overdue': CHART_COLORS['overdue'],
}


class CouncilReport(FPDF):
    def footer(self):
        self.set_y(-13)
        self.set_draw_color(*REPORT_RULE)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.set_font('Tajawal', size=9)
        self.set_text_color(86, 106, 101)
        self.cell(w=self.epw, h=8, text=f'صفحة {self.page_no()}', align='C')


def draw_report_header(pdf, context):
    council = context['council']
    name = getattr(council, 'name', None) or council['name']
    logo = getattr(council, 'logo', None)
    right = pdf.w - pdf.r_margin
    top = pdf.get_y()
    text_width = pdf.epw
    if logo:
        try:
            with logo.storage.open(logo.name, 'rb') as source, Image.open(source) as image:
                image.thumbnail((512, 512))
                pdf.image(image.convert('RGBA'), x=right - 24, y=top, w=24, h=24, keep_aspect_ratio=True)
            text_width -= 30
        except (OSError, ValueError, Image.DecompressionBombError):
            logger.warning('Could not load the council logo for the report', exc_info=True)

    pdf.set_text_color(*REPORT_INK)
    pdf.set_font('Tajawal', 'B', 12)
    pdf.multi_cell(w=text_width, h=6, text=name, align='R', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Tajawal', 'B', 20)
    pdf.cell(w=text_width, h=10, text=context['title'], align='R', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Tajawal', size=10)
    generated = timezone.localtime(context['generated_at']).strftime('%Y/%m/%d %H:%M')
    pdf.cell(w=text_width, h=6, text=f'تاريخ التوليد: \u2066{generated}\u2069', align='R', new_x='LMARGIN', new_y='NEXT')
    y = max(pdf.get_y(), top + 24) + 3
    pdf.set_draw_color(*REPORT_RULE)
    pdf.line(pdf.l_margin, y, right, y)
    pdf.set_y(y + 3)


def chart_heading(pdf, chart):
    pdf.ln(4)
    pdf.set_font('Tajawal', 'B', 14)
    pdf.cell(w=pdf.epw, h=7, text=chart['title'], align='R', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Tajawal', size=10)
    pdf.cell(w=pdf.epw, h=5, text=chart['caption'], align='R', new_x='LMARGIN', new_y='NEXT')


def draw_chart(pdf, chart):
    rows = chart['rows']
    variant = chart['variant']
    if variant == 'departments' and rows:
        draw_department_chart(pdf, chart)
        return

    height = 70 if variant == 'weekly' else 22 + 11 * len(rows)
    if pdf.will_page_break(height):
        pdf.add_page()
    chart_heading(pdf, chart)
    if not rows:
        pdf.cell(w=pdf.epw, h=6, text='لا توجد بيانات لعرضها.', align='R', new_x='LMARGIN', new_y='NEXT')
    elif variant == 'weekly':
        draw_weekly_chart(pdf, chart)
    else:
        for row in rows:
            pdf.multi_cell(w=pdf.epw, h=5, text=row['label'], align='R', new_x='LMARGIN', new_y='NEXT')
            value = str(row['count'])
            if row['share'] is not None:
                value += f"  ({row['share']}٪)"
            draw_horizontal_bar(pdf, row['percent'], value, CHART_COLORS[variant])
            pdf.ln(1)


def draw_horizontal_bar(pdf, percent, value, color, label_width=0):
    count_width = 25
    track_width = pdf.epw - count_width - label_width
    right = pdf.w - pdf.r_margin - label_width
    y = pdf.get_y()
    pdf.set_fill_color(*CHART_TRACK)
    pdf.rect(right - track_width, y + 1, track_width, 2.5, style='F')
    if percent:
        width = track_width * percent / 100
        pdf.set_fill_color(*color)
        pdf.rect(right - width, y + 1, width, 2.5, style='F')
    pdf.cell(w=count_width, h=5, text=value, align='L', new_x='LMARGIN', new_y='NEXT')


def draw_department_chart(pdf, chart):
    def start_chart():
        chart_heading(pdf, chart)
        pdf.ln(2)

    label_width = 33
    if pdf.will_page_break(48):
        pdf.add_page()
    start_chart()
    for row in chart['rows']:
        if pdf.will_page_break(30):
            pdf.add_page()
            start_chart()
        pdf.set_font('Tajawal', 'B', 11)
        pdf.multi_cell(w=pdf.epw, h=5, text=row['label'], align='R', new_x='LMARGIN', new_y='NEXT')
        pdf.set_font('Tajawal', size=9)
        for segment in row['segments']:
            y = pdf.get_y()
            pdf.set_x(pdf.w - pdf.r_margin - label_width)
            pdf.cell(w=label_width, h=5, text=segment['label'], align='R')
            pdf.set_xy(pdf.l_margin, y)
            draw_horizontal_bar(
                pdf, segment['percent'], str(segment['count']), DEPARTMENT_COLORS[segment['key']], label_width,
            )
        pdf.ln(3)


def draw_weekly_chart(pdf, chart):
    rows = chart['rows']
    axis_width = 9
    plot_width = pdf.epw - axis_width
    column_width = plot_width / len(rows)
    track_height = 34
    top = pdf.get_y() + 8
    left = pdf.l_margin
    right = left + plot_width
    baseline = top + track_height
    maximum = chart['ticks'][-1]

    pdf.set_draw_color(*REPORT_RULE)
    pdf.set_font('Tajawal', size=9)
    for tick in chart['ticks']:
        y = baseline - track_height * tick / maximum
        pdf.line(left, y, right, y)
        pdf.set_xy(right, y - 2.5)
        pdf.cell(w=axis_width, h=5, text=str(tick), align='R')
    for index, row in enumerate(rows):
        x = right - (index + 1) * column_width
        bar_width = column_width * 0.49
        bar_x = x + (column_width - bar_width) / 2
        bar_height = track_height * row['count'] / maximum
        if bar_height:
            pdf.set_fill_color(*CHART_COLORS['weekly'])
            pdf.rect(bar_x, baseline - bar_height, bar_width, bar_height, style='F')
        pdf.set_xy(x, baseline - bar_height - 5)
        pdf.cell(w=column_width, h=5, text=str(row['count']), align='C')
        pdf.set_xy(x, baseline + 1)
        pdf.cell(w=column_width, h=5, text=row['label'], align='C')
    pdf.set_xy(left, baseline + 8)


def report_pdf(context):
    pdf = CouncilReport()
    pdf.set_margins(15, 15, 15)
    pdf.set_lang('ar')
    pdf.set_title(context['title'])
    fonts = settings.BASE_DIR / 'core' / 'static' / 'core' / 'fonts'
    pdf.add_font('Tajawal', fname=fonts / 'tajawal-regular.ttf')
    pdf.add_font('Tajawal', style='B', fname=fonts / 'tajawal-bold.ttf')
    pdf.set_text_shaping(True)
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    draw_report_header(pdf, context)

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
        # FPDF initializes table styles from the current fill color.
        pdf.set_fill_color(255, 255, 255)
        pdf.set_draw_color(*REPORT_RULE)
        with pdf.table(
            col_widths=tuple(reversed(widths)),
            headings_style=FontFace(emphasis='BOLD', fill_color=REPORT_HEADER),
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

    section('الوارد حسب الأسبوع', ('بداية الأسبوع', 'الشكاوى الواردة'),
            ((row['week'].strftime('%Y/%m/%d'), row['count']) for row in context['weekly_rows']), (3, 1))
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
