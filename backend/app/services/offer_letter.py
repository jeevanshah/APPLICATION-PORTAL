"""
Offer letter generation service using ReportLab for PDF creation.
Generates professional offer letters for approved applications.
"""
import os
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, Optional
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from app.models import Application, RtoProfile


class OfferLetterService:
    """Service for generating offer letter PDFs."""
    
    def __init__(self, output_dir: str = "uploads/offer_letters"):
        """
        Initialize offer letter service.
        
        Args:
            output_dir: Directory to save generated PDFs
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_offer_letter(
        self,
        application: Application,
        offer_details: Dict[str, Any],
        rto_profile: RtoProfile
    ) -> str:
        """
        Generate offer letter PDF for approved application.
        
        Args:
            application: Application record
            offer_details: Dict with course_start_date, tuition_fee, material_fee, conditions, etc.
            rto_profile: RTO organization profile
        
        Returns:
            File path to generated PDF
        """
        # Generate filename
        student_name = f"{application.student.given_name}_{application.student.family_name}"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"offer_letter_{student_name}_{timestamp}.pdf"
        filepath = self.output_dir / filename
        
        # Create PDF document
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        # Build content
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#003366'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#003366'),
            spaceAfter=12,
            spaceBefore=16
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['BodyText'],
            fontSize=11,
            leading=14,
            spaceAfter=12
        )
        
        # Add RTO header
        story.append(Paragraph(rto_profile.name.upper(), title_style))
        
        if rto_profile.address:
            address_text = self._format_address(rto_profile.address)
            story.append(Paragraph(address_text, ParagraphStyle('Address', parent=body_style, alignment=TA_CENTER, fontSize=10)))
        
        if rto_profile.cricos_code:
            story.append(Paragraph(f"CRICOS Provider Code: {rto_profile.cricos_code}", 
                                 ParagraphStyle('CRICOS', parent=body_style, alignment=TA_CENTER, fontSize=10)))
        
        story.append(Spacer(1, 0.3*inch))
        
        # Date
        offer_date = datetime.now().strftime("%d %B %Y")
        story.append(Paragraph(offer_date, ParagraphStyle('Date', parent=body_style, alignment=TA_RIGHT, fontSize=10)))
        story.append(Spacer(1, 0.2*inch))
        
        # Student details
        student = application.student
        story.append(Paragraph(f"{student.given_name} {student.family_name}", heading_style))
        if student.address:
            story.append(Paragraph(student.address, body_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Offer letter title
        story.append(Paragraph("<b>LETTER OF OFFER</b>", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Opening paragraph
        opening = f"""
        Dear {student.given_name} {student.family_name},<br/><br/>
        
        We are pleased to offer you a place in the following course at {rto_profile.name}. 
        This offer is made subject to the conditions outlined in this letter.
        """
        story.append(Paragraph(opening, body_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Course details table
        course = application.course
        course_start_date = offer_details.get('course_start_date', 'TBD')
        if isinstance(course_start_date, (date, datetime)):
            course_start_date = course_start_date.strftime("%d %B %Y")
        
        tuition_fee = offer_details.get('tuition_fee', course.tuition_fee)
        material_fee = offer_details.get('material_fee', 0.0)
        total_fee = float(tuition_fee) + float(material_fee)
        
        course_data = [
            ['<b>Course Details</b>', ''],
            ['Course Name:', course.course_name],
            ['Course Code:', course.course_code],
            ['Intake:', course.intake],
            ['Campus:', course.campus],
            ['Course Start Date:', str(course_start_date)],
            ['', ''],
            ['<b>Fees (AUD)</b>', ''],
            ['Tuition Fee:', f"${tuition_fee:,.2f}"],
        ]
        
        if material_fee > 0:
            course_data.append(['Material Fee:', f"${material_fee:,.2f}"])
        
        course_data.append(['<b>Total Course Fee:</b>', f"<b>${total_fee:,.2f}</b>"])
        
        course_table = Table(course_data, colWidths=[3*inch, 3*inch])
        course_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        
        story.append(course_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Conditions of offer
        story.append(Paragraph("<b>Conditions of Offer</b>", heading_style))
        
        conditions = offer_details.get('conditions', [
            "Payment of tuition fees as per payment plan",
            "Provision of certified copies of all academic transcripts and certificates",
            "Valid student visa (for international students)",
            "Overseas Student Health Cover (OSHC) for the duration of the course",
            "Compliance with the RTO's policies and code of conduct"
        ])
        
        for i, condition in enumerate(conditions, 1):
            story.append(Paragraph(f"{i}. {condition}", body_style))
        
        story.append(Spacer(1, 0.2*inch))
        
        # Acceptance instructions
        story.append(Paragraph("<b>Acceptance of Offer</b>", heading_style))
        acceptance_text = f"""
        To accept this offer, please:<br/>
        1. Sign and return this letter by email to {rto_profile.contact_email}<br/>
        2. Pay the required fees as per the payment schedule<br/>
        3. Complete the online enrolment form<br/>
        <br/>
        This offer remains valid for 30 days from the date of this letter.
        """
        story.append(Paragraph(acceptance_text, body_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Closing
        closing = f"""
        We look forward to welcoming you to {rto_profile.name}.<br/><br/>
        
        Sincerely,<br/><br/><br/>
        
        <b>Admissions Office</b><br/>
        {rto_profile.name}<br/>
        Email: {rto_profile.contact_email}<br/>
        Phone: {rto_profile.contact_phone}
        """
        story.append(Paragraph(closing, body_style))
        story.append(Spacer(1, 0.5*inch))
        
        # Student acceptance signature section
        signature_data = [
            ['<b>Student Acceptance</b>', ''],
            ['', ''],
            ['I accept the offer as outlined above:', ''],
            ['', ''],
            ['Student Signature: ___________________________', 'Date: _______________'],
            ['', ''],
            [f'Student Name: {student.given_name} {student.family_name}', '']
        ]
        
        signature_table = Table(signature_data, colWidths=[4*inch, 2*inch])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 2), (0, 2), 6),
            ('TOPPADDING', (0, 3), (0, 3), 12),
        ]))
        
        story.append(signature_table)
        
        # Build PDF
        doc.build(story)
        
        return str(filepath)
    
    def _format_address(self, address: Dict[str, Any]) -> str:
        """Format address dictionary as string."""
        parts = []
        if address.get('street'):
            parts.append(address['street'])
        if address.get('city'):
            city_state = address['city']
            if address.get('state'):
                city_state += f", {address['state']}"
            if address.get('postcode'):
                city_state += f" {address['postcode']}"
            parts.append(city_state)
        if address.get('country'):
            parts.append(address['country'])
        return "<br/>".join(parts)
