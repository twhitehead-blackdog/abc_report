from odoo import fields, models, api, _

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    from odoo.addons.setu_abc_analysis_reports.library import xlsxwriter
from . import setu_excel_formatter
import base64
from io import BytesIO


class SetuInventoryXYZAnalysisReport(models.TransientModel):
    _name = 'setu.inventory.xyz.analysis.report'
    _description = """
        XYZ Analysis is always done for the current Stock in Inventory and aims at classifying the items into three classes on the basis of their Inventory values. 
        The current value of the items/variants in the Inventory alone is taken into consideration for the Analysis and it is not possible to do this analysis for any other dates. 
        
        First 70% of the total Inventory value corresponds to X Class 
        Next 20% are of Y Class 
        Last 10% of the value corresponds to the Z Class.
    """

    stock_file_data = fields.Binary('Stock Movement File')
    company_ids = fields.Many2many("res.company", string="Companies")
    product_category_ids = fields.Many2many("product.category", string="Product Categories")
    product_ids = fields.Many2many("product.product", string="Products")
    inventory_analysis_type = fields.Selection([('all', 'All'),
                                                ('high_stock', 'X Class'),
                                                ('medium_stock', 'Y Class'),
                                                ('low_stock', 'Z Class')], "XYZ Classification", default="all")


    @staticmethod
    def get_file_name():
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method will use for prepare workbook and return excel workbook
        :return:
        """
        filename = "inventory_xyz_analysis_report.xlsx"
        return filename

    @staticmethod
    def create_excel_workbook(file_pointer):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method will use for create worksheet and return excel workbook
        :param file_pointer:
        :return:
        """
        workbook = xlsxwriter.Workbook(file_pointer)
        return workbook

    @staticmethod
    def create_excel_worksheet(workbook, sheet_name):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method will use for prepare worksheet with specific rows
        :param workbook:
        :param sheet_name:
        :return:
        """
        worksheet = workbook.add_worksheet(sheet_name)
        worksheet.set_default_row(22)
        # worksheet.set_border()
        return worksheet

    @staticmethod
    def set_column_width(worksheet):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method will use for set column width in xls worksheet
        :param worksheet:
        :return:
        """
        worksheet.set_column(0, 1, 25)
        worksheet.set_column(2, 6, 16)

    @staticmethod
    def set_format(workbook, wb_format):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method will use prepare format for title in xls worksheet
        :param workbook:
        :param wb_format:
        :return:
        """
        wb_new_format = workbook.add_format(wb_format)
        wb_new_format.set_border()
        return wb_new_format

    def set_report_title(self, workbook, worksheet):
        """
            Author: Kinnari Tank | Date: 11th Oct,2024 | Task: 1000
            Purpose: THis method will use for prepare title in xls worksheet
        :param workbook:
        :param worksheet:
        :return:
        """
        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_TITLE_CENTER)
        worksheet.merge_range(0, 0, 1, 6, "Inventory XYZ Analysis Report", wb_format)

    def get_inventory_xyz_analysis_report_data(self):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method will use for fetch data from query based on user inputs.
        :return:
        """
        category_ids = company_ids = {}
        if self.product_category_ids:
            categories = self.env['product.category'].search([('id', 'child_of', self.product_category_ids.ids)])
            category_ids = set(categories.ids) or {}
        products = self.product_ids and set(self.product_ids.ids) or {}

        if self.company_ids:
            companies = self.env['res.company'].search([('id', 'child_of', self.company_ids.ids)])
            company_ids = set(companies.ids) or {}
        else:
            company_ids = set(self.env.context.get('allowed_company_ids', False) or self.env.user.company_ids.ids) or {}

        # get_products_overstock_data(company_ids, product_ids, category_ids, warehouse_ids, start_date, end_date, advance_stock_days)
        query = """
                Select * from get_inventory_xyz_analysis_data('%s','%s','%s', '%s')
            """ % (company_ids, products, category_ids, self.inventory_analysis_type)
        # print(query)
        self._cr.execute(query)
        stock_data = self._cr.dictfetchall()
        return stock_data

    def prepare_data_to_write(self, stock_data={}):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method will use for prepare company wise data to generate company wise result
        :param stock_data:
        :return:
        """
        warehouse_wise_data = {}
        for data in stock_data:
            key = (data.get('company_id'), data.get('company_name'))
            if not warehouse_wise_data.get(key, False):
                warehouse_wise_data[key] = {data.get('product_id'): data}
            else:
                warehouse_wise_data.get(key).update({data.get('product_id'): data})
        return warehouse_wise_data

    def download_report(self):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method return xls worksheet when user click on excel report button from wizard.
        :return:
        """
        file_name = self.get_file_name()
        file_pointer = BytesIO()
        stock_data = self.get_inventory_xyz_analysis_report_data()
        warehouse_wise_analysis_data = self.prepare_data_to_write(stock_data=stock_data)
        if not warehouse_wise_analysis_data:
            return False
        workbook = self.create_excel_workbook(file_pointer)
        for stock_data_key, stock_data_value in warehouse_wise_analysis_data.items():
            sheet_name = stock_data_key[1]
            wb_worksheet = self.create_excel_worksheet(workbook, sheet_name)
            row_no = 3
            self.write_report_data_header(workbook, wb_worksheet, row_no)
            for xyz_data_key, xyz_data_value in stock_data_value.items():
                row_no = row_no + 1
                self.write_data_to_worksheet(workbook, wb_worksheet, xyz_data_value, row=row_no)
        # workbook.save(file_name)
        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'stock_file_data': file_data})
        file_pointer.close()
        return {
            'name': 'Inventory XYZ Analysis Report',
            'type': 'ir.actions.act_url',
            'url': '/web/binary/setu_abc_download_document?model=setu.inventory.xyz.analysis.report&field=stock_file_data&id=%s&filename=%s' % (
            self.id, file_name),
            'target': 'self',
        }

    def download_report_in_listview(self):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method will use for return list view when user click on view data button from wizard
            and return graph view of reports when user click on view graph button from wizard.
        :return:
        """
        stock_data = self.get_inventory_xyz_analysis_report_data()
        #print(stock_data)
        for xyz_data_value in stock_data:
            xyz_data_value['wizard_id'] = self.id
            self.create_data(xyz_data_value)
        graph_view_id = self.env.ref('setu_abc_analysis_reports.setu_inventory_xyz_analysis_bi_report_graph').id
        list_view_id = self.env.ref('setu_abc_analysis_reports.setu_inventory_xyz_analysis_bi_report_list').id
        is_graph_first = self.env.context.get('graph_report', False)
        report_display_views = []
        viewmode = ''
        if is_graph_first:
            report_display_views.append((graph_view_id, 'graph'))
            report_display_views.append((list_view_id, 'list'))
            viewmode = "graph,list"
        else:
            report_display_views.append((list_view_id, 'list'))
            report_display_views.append((graph_view_id, 'graph'))
            viewmode = "list,graph"
        return {
            'name': _('Inventory XYZ Analysis'),
            'domain': [('wizard_id', '=', self.id)],
            'res_model': 'setu.inventory.xyz.analysis.bi.report',
            'view_mode': viewmode,
            'type': 'ir.actions.act_window',
            'views': report_display_views,
        }

    def create_data(self, data):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method will use for remove specific records from data
            and create record in bi report module
        :param data:
        :return:
        """
        del data['company_name']
        del data['product_name']
        del data['category_name']
        del data['cum_stock_value_per']
        return self.env['setu.inventory.xyz.analysis.bi.report'].create(data)

    def write_report_data_header(self, workbook, worksheet, row):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method will use for add header in xls worksheet with highlighting color and background
        :param workbook:
        :param worksheet:
        :param row:
        :return:
        """
        self.set_report_title(workbook, worksheet)
        self.set_column_width(worksheet)
        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)
        wb_format.set_text_wrap()

        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_BOLD_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_BOLD_RIGHT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)
        worksheet.write(row, 0, 'Product', normal_left_format)
        worksheet.write(row, 1, 'Category', normal_left_format)
        worksheet.write(row, 2, 'Company', normal_left_format)
        worksheet.write(row, 3, 'Current Stock', even_normal_right_format)
        worksheet.write(row, 4, 'Stock Value', odd_normal_right_format)
        worksheet.write(row, 5, 'Stock Value (%)', even_normal_right_format)
        # worksheet.write(row, 6, 'Cumulative (%)', even_normal_right_format)
        worksheet.write(row, 6, 'XYZ Classification', odd_normal_right_format)
        return worksheet

    def write_data_to_worksheet(self, workbook, worksheet, data, row):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method will use for add records in worksheet with appropriate format
        :param workbook:
        :param worksheet:
        :param data:
        :param row:
        :return:
        """
        # Start from the first cell. Rows and
        # columns are zero indexed.
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_RIGHT)
        odoo_normal_center_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_CENTER)
        odd_normal_left_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_LEFT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_NORMAL_LEFT)
        worksheet.write(row, 0, data.get('product_name', ''), normal_left_format)
        worksheet.write(row, 1, data.get('category_name', ''), normal_left_format)
        worksheet.write(row, 2, data.get('company_name', ''), normal_left_format)
        worksheet.write(row, 3, data.get('current_stock', ''), even_normal_right_format)
        worksheet.write(row, 4, data.get('stock_value', ''), odd_normal_right_format)
        worksheet.write(row, 5, data.get('stock_value_per', ''), even_normal_right_format)
        # worksheet.write(row, 6, data.get('cum_stock_value_per', ''), even_normal_right_format)
        worksheet.write(row, 6, data.get('analysis_category', ''), odoo_normal_center_format)
        return worksheet
