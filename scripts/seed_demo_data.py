"""Demo dataset generator seeding fictional products, specifications, documents, criteria, and complaints."""
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from datetime import datetime, date, timedelta
from src.database.connection import get_db
from src.database.schema import init_db
from src.auth.service import create_user
from src.products.service import create_customer, create_product, set_customer_product_spec
from src.quality_engine.criteria_manager import create_quality_criterion
from src.complaint_management.service import create_complaint, update_complaint_status
from src.document_processing.service import ingest_document
from src.quality_engine.rule_evaluator import evaluate_complaint
from src.compliance.risk_matrix import calculate_complaint_risk
from src.quality_engine.root_cause import generate_root_cause_hypotheses
from src.complaint_management.capa import create_capa_task, auto_suggest_capas
from src.quality_engine.approval import review_evaluation

def seed_all_demo_data(reset: bool = True):
    """Initializes the database and populates comprehensive, clearly labeled fictional demo data."""
    print("Initializing Database Schema...")
    init_db()

    if reset:
        print("Resetting existing demo records...")
        with get_db() as conn:
            # Delete in foreign key dependency order
            conn.execute("DELETE FROM audit_logs")
            conn.execute("DELETE FROM capa_tasks")
            conn.execute("DELETE FROM root_cause_hypotheses")
            conn.execute("DELETE FROM risk_assessments")
            conn.execute("DELETE FROM evaluation_criteria_results")
            conn.execute("DELETE FROM evaluations")
            conn.execute("DELETE FROM complaint_status_history")
            conn.execute("DELETE FROM complaint_attachments")
            conn.execute("DELETE FROM complaints")
            conn.execute("DELETE FROM quality_criteria")
            conn.execute("DELETE FROM document_chunks")
            conn.execute("DELETE FROM document_fts")
            conn.execute("DELETE FROM documents")
            conn.execute("DELETE FROM product_customer_specs")
            conn.execute("DELETE FROM products")
            conn.execute("DELETE FROM users")
            conn.execute("DELETE FROM customers")

    print("1. Creating Users & Roles...")
    # Default password for all demo accounts: 'Quality2026!'
    pwd = "Quality2026!"
    u_admin = create_user("admin", pwd, "System Administrator", "admin@codespace-techlab.demo", "Admin")
    u_mgr = create_user("manager1", pwd, "Sarah Jenkins (Quality Manager)", "sjenkins@codespace-techlab.demo", "Quality Manager")
    u_eng = create_user("engineer1", pwd, "Marcus Chen (QA Engineer)", "mchen@codespace-techlab.demo", "Quality Engineer")
    u_view = create_user("viewer1", pwd, "David Rossi (Operations Director)", "drossi@codespace-techlab.demo", "Management Viewer")

    print("2. Creating Customers & Retailers...")
    c_ikea = create_customer("CUST-IKEA", "IKEA Global Supply Chain (Fictional Partner Demo)", "IKEA", "Henrik Lindqvist", "henrik.l@ikea-supply.demo", "Major retail partner. Strict IWAY and flat-pack packaging requirements.")
    c_target = create_customer("CUST-TGT", "Target Home Distribution (Fictional Partner Demo)", "Retailer", "Jessica Davis", "jdavis@target-retail.demo", "North American retail partner.")
    c_direct = create_customer("CUST-DIR", "Direct Enterprise Client (Fictional Partner Demo)", "Direct Customer", "Robert Keller", "rkeller@direct-furnishings.demo", "Direct contract sales.")

    # Create customer-isolated user
    u_ikea = create_user("ikea_rep", pwd, "Elin Bergstrom (IKEA Quality Inspector)", "elin.b@ikea-supply.demo", "Customer", customer_id=c_ikea)

    print("3. Creating Product Catalog...")
    p_table = create_product(
        sku="NDT-800",
        name="Nordic Oak Dining Table NDT-800 (Fictional Demo)",
        category="Dining Furniture",
        description="Solid European white oak dining table with bevelled perimeter, flat-pack steel reinforcement brackets, and non-toxic matte lacquer.",
        materials_summary="Kiln-dried European Oak (Quercus robur), Powder-coated carbon steel brackets, Water-based polyurethane finish.",
        batch_prefix="LOT-NDT",
        target_market="EU & North America",
        revision="1.2",
        status="Active",
        user_id=u_admin
    )

    p_chair = create_product(
        sku="ETC-450",
        name="ErgoFlex Task Chair ETC-450 (Fictional Demo)",
        category="Office Seating",
        description="High-performance ergonomic task chair with synchronous tilt mechanism, adjustable 3D lumbar support, Class 4 gas lift, and breathable nylon mesh.",
        materials_summary="PA6 nylon frame, 65kg/m3 cold-cure molded polyurethane foam, Korean Class 4 nitrogen gas cylinder, Glass-filled nylon 5-star base.",
        batch_prefix="LOT-ETC",
        target_market="Global Commercial",
        revision="1.0",
        status="Active",
        user_id=u_admin
    )

    p_cabinet = create_product(
        sku="AGC-120",
        name="Aura Glass Display Cabinet AGC-120 (Fictional Demo)",
        category="Storage & Cabinets",
        description="Floor-standing display cabinet featuring 5mm tempered safety glass, integrated LED channel, and matte black anodized aluminum framing.",
        materials_summary="5mm EN 12150-1 tempered glass, 6063-T5 aluminum extrusions, Neodymium magnetic door latches.",
        batch_prefix="LOT-AGC",
        target_market="EU & UK",
        revision="1.0",
        status="Active",
        user_id=u_admin
    )

    print("4. Setting Customer-Specific Requirements...")
    set_customer_product_spec(
        product_id=p_table,
        customer_id=c_ikea,
        spec_code="IKEA-SPEC-W01",
        specific_requirements="Table edge radius minimum 3.0mm; packaging must incorporate 5-layer honeycomb corrugated corner guards; flat-pack multi-language visual instructions leaflet Rev 4.",
        notes="Mandatory for all shipments to European IKEA distribution centers.",
        user_id=u_admin
    )
    set_customer_product_spec(
        product_id=p_chair,
        customer_id=c_target,
        spec_code="TGT-SPEC-SEAT",
        specific_requirements="136 kg dynamic load rating tested per ANSI/BIFMA X5.1; California TB 117-2013 flammability compliant sewn-in label.",
        notes="Retail packaging must include full color bilingual outer carton.",
        user_id=u_admin
    )

    print("5. Ingesting Approved Knowledge Base Documents...")
    # Document 1: Table Approved Spec
    doc1_content = """# APPROVED PRODUCT SPECIFICATION: NORDIC OAK DINING TABLE (SKU: NDT-800)
Revision: 1.2 | Effective Date: 2026-01-15 | Status: APPROVED
Manufacturer: Code Space Techlab | Intended Market: Global

## 1. Dimensional Standards & Tolerances
- Length: Nominal 2000 mm (Allowable tolerance: +/- 5.0 mm, Range [1995.0 mm, 2005.0 mm])
- Width: Nominal 950 mm (Allowable tolerance: +/- 4.0 mm, Range [946.0 mm, 954.0 mm])
- Height / Clearance: Nominal 750 mm (Allowable tolerance: +/- 5.0 mm, Range [745.0 mm, 755.0 mm])
- Tabletop Thickness: Nominal 32 mm (+/- 1.0 mm)
- Leg Square Cross-Section: 80 mm x 80 mm (+/- 1.0 mm)

## 2. Raw Material Requirements
- Timber Species: European White Oak (Quercus robur), FSC 100% Certified.
- Moisture Content: Moisture content must be strictly controlled between 8.0% and 12.0% at time of final packaging. Moisture levels above 12.5% represent a critical non-conformance causing severe warping.
- Surface Imperfections: Pin knots under 10 mm allowed if factory filled with epoxy. Cracks, shake, or open splits are strictly prohibited.

## 3. Surface Finish & Visual Quality
- Coating: 3-coat matte water-based acrylic-polyurethane UV lacquer (Gloss level 10-15%).
- Adhesion: Cross-hatch adhesion test per ISO 2409 must achieve Class 0 (no detachment).
- Surface Flaws: Free of blisters, orange peel, orange staining, rough sanding marks, and gouges. Scratches exceeding 1.0 mm length or depth are rejected.
"""
    ingest_document(
        file_bytes=doc1_content.encode("utf-8"),
        file_name="NDT-800_Approved_Specification_Rev1.2.txt",
        product_id=p_table,
        category="Product Specification",
        title="NDT-800 Engineering Specification (Rev 1.2)",
        revision="1.2",
        effective_date="2026-01-15",
        expiry_date="2027-01-15",
        approval_status="Approved",
        user_id=u_admin
    )

    # Document 2: Table REACH Chemical Compliance
    doc2_content = """# CHEMICAL SAFETY & REACH COMPLIANCE DECLARATION (SKU: NDT-800)
Document Ref: CST-CHM-NDT-2026 | Revision: 1.0 | Status: APPROVED
Standards: EU REACH Regulation (EC) No 1907/2006, EN 717-1 Formaldehyde Emissions

## 1. SVHC Substance Declaration
Code Space Techlab certifies that the Nordic Oak Dining Table (NDT-800) does not contain any Substances of Very High Concern (SVHC) on the ECHA Candidate List in concentrations exceeding 0.1% (w/w).

## 2. Formaldehyde Emission Testing (EN 717-1)
- Testing Method: 1 m³ climate chamber method per EN 717-1.
- Mandatory Acceptance Limit: Formaldehyde emission must not exceed 0.05 mg/m³ air (half of European E1 standard).
- Certified Laboratory Test Value: Batch LOT-NDT tested at 0.021 mg/m³ air (PASS).

## 3. Volatile Organic Compounds (VOC)
- Total VOC emissions after 28 days: < 0.20 mg/m³ per ISO 16000-9.
- Heavy Metals (Lead, Cadmium, Mercury): Below limit of detection (< 5 ppm) per EN 71-3.
"""
    ingest_document(
        file_bytes=doc2_content.encode("utf-8"),
        file_name="NDT-800_Chemical_REACH_Safety_Rev1.0.txt",
        product_id=p_table,
        category="Chemical Safety & REACH",
        title="NDT-800 REACH & Chemical Safety Declaration",
        revision="1.0",
        effective_date="2026-01-01",
        expiry_date="2027-01-01",
        approval_status="Approved",
        user_id=u_admin
    )

    # Document 3: IKEA Specific Packaging Requirements for NDT-800
    doc3_content = """# CUSTOMER REQUIREMENT STANDARD: IKEA PACKAGING & LOGISTICS SPECIFICATION
Document ID: IKEA-SPEC-W01 | Customer: IKEA Global Supply Chain | Applicable SKU: NDT-800
Revision: 2.1 | Effective Date: 2026-02-01 | Status: APPROVED

## 1. Transit Protection & Drop Testing
- Corner Protection: All eight exterior box corners must be fitted with 10 mm high-density recycled honeycomb U-profile corner protectors. Missing corner protectors constitute an immediate audit failure.
- Carton Bursting Strength: Double-wall BC-flute corrugated cardboard, Mullen burst test rating minimum 1400 kPa.
- Drop Test Acceptance: ISTA 3A sequence completed with zero component damage.

## 2. Flat-Pack Fastener Kits & Hardware
- All dowels, M8 hex bolts, Allen keys, and rubber floor-glide pads must be sealed in heavy gauge transparent polybag clearly heat-stamped with lot number.
- Inspection Rule: Zero missing hardware tolerance. Every carton must pass online weight-check verification (+/- 15 grams).
"""
    ingest_document(
        file_bytes=doc3_content.encode("utf-8"),
        file_name="NDT-800_IKEA_Packaging_Requirement_Rev2.1.txt",
        product_id=p_table,
        customer_id=c_ikea,
        category="Customer-Specific Requirement",
        title="IKEA Flat-Pack Packaging & Corner Protection Standard (Rev 2.1)",
        revision="2.1",
        effective_date="2026-02-01",
        expiry_date="2027-02-01",
        approval_status="Approved",
        user_id=u_admin
    )

    # Document 4: Task Chair ETC-450 Specification
    doc4_content = """# PRODUCT SPECIFICATION & BIFMA TEST STANDARD: ERGOFLEX TASK CHAIR (ETC-450)
Revision: 1.0 | Status: APPROVED | Applicable SKU: ETC-450

## 1. Mechanism & Stroke Travel
- Gas Lift Travel: Nominal travel 120 mm. Seat height adjustment range must be within [450.0 mm, 570.0 mm].
- Swivel & Rotation: 360 degree smooth rotation with zero axial play exceeding 1.5 degrees.
- Class 4 Nitrogen Cylinder: Proof tested to DIN 4550 Class 4 standards (minimum wall thickness 2.5 mm). Cylinder slipping or downward creeping under 100 kg static load is a critical safety failure.

## 2. Durability & Cyclic Fatigue (ANSI/BIFMA X5.1)
- Cyclic Seating Impact: 100,000 cycles with 102 kg bag dropped from 36 mm. No loss of structural integrity.
- Armrest Vertical Load: 100 kg proof load applied simultaneously to both armrests without permanent deformation.
- Castor Durability: 100,000 cycles on obstacle course without loss of wheel retention.
"""
    ingest_document(
        file_bytes=doc4_content.encode("utf-8"),
        file_name="ETC-450_Product_Spec_and_BIFMA_Rev1.0.txt",
        product_id=p_chair,
        category="Product Specification",
        title="ETC-450 Task Chair Engineering & BIFMA Standard",
        revision="1.0",
        effective_date="2026-01-10",
        expiry_date="2027-01-10",
        approval_status="Approved",
        user_id=u_admin
    )

    print("6. Configuring Configurable Quality Criteria...")
    create_quality_criterion(
        criterion_code="CRIT-DIM-01",
        name="Tabletop Length Specification",
        category="Dimensional & Tolerances",
        criterion_type="Numeric Range",
        product_id=p_table,
        measurement_unit="mm",
        min_allowed=1995.0,
        max_allowed=2005.0,
        weight=2.0,
        severity="Critical",
        is_mandatory=True,
        description="Length of solid oak tabletop must remain strictly between 1995mm and 2005mm.",
        user_id=u_admin
    )

    create_quality_criterion(
        criterion_code="CRIT-DIM-02",
        name="Table Clearance Height",
        category="Dimensional & Tolerances",
        criterion_type="Numeric Range",
        product_id=p_table,
        measurement_unit="mm",
        min_allowed=745.0,
        max_allowed=755.0,
        weight=2.0,
        severity="Critical",
        is_mandatory=True,
        description="Assembled clearance height from floor to top edge must be between 745mm and 755mm.",
        user_id=u_admin
    )

    create_quality_criterion(
        criterion_code="CRIT-MAT-01",
        name="Oak Timber Moisture Content",
        category="Material & Chemical",
        criterion_type="Numeric Range",
        product_id=p_table,
        measurement_unit="%",
        min_allowed=8.0,
        max_allowed=12.0,
        weight=3.0,
        severity="Critical",
        is_mandatory=True,
        description="Moisture meter core reading must be between 8% and 12% to prevent seasonal wood splitting.",
        user_id=u_admin
    )

    create_quality_criterion(
        criterion_code="CRIT-CHM-01",
        name="Chemical Safety & REACH Declaration Present",
        category="Documentation & Compliance",
        criterion_type="Required Document",
        product_id=p_table,
        expected_value="Chemical Safety & REACH",
        weight=2.5,
        severity="Critical",
        is_mandatory=True,
        description="Approved REACH SVHC chemical safety declaration must be valid and on file.",
        user_id=u_admin
    )

    create_quality_criterion(
        criterion_code="CRIT-PKG-01",
        name="Honeycomb Corner Protectors Present",
        category="Packaging & Labeling",
        criterion_type="Boolean Check",
        product_id=p_table,
        customer_id=c_ikea,
        weight=1.5,
        severity="Major",
        is_mandatory=True,
        description="All eight corners must have high-density honeycomb protective caps per IKEA-SPEC-W01.",
        user_id=u_admin
    )

    create_quality_criterion(
        criterion_code="CRIT-VIS-01",
        name="Aesthetic Surface Finish & Scratch Absence",
        category="Visual & Aesthetic",
        criterion_type="Qualitative",
        product_id=p_table,
        weight=1.0,
        severity="Minor",
        is_mandatory=False,
        description="Tabletop lacquer must be uniform, free of peeling, bubbling, and scratches > 1mm.",
        user_id=u_admin
    )

    create_quality_criterion(
        criterion_code="CRIT-GAS-01",
        name="Chair Gas Lift Height Travel Range",
        category="Dimensional & Tolerances",
        criterion_type="Numeric Range",
        product_id=p_chair,
        measurement_unit="mm",
        min_allowed=450.0,
        max_allowed=570.0,
        weight=2.5,
        severity="Critical",
        is_mandatory=True,
        description="Seat height travel range must adjust smoothly between 450mm and 570mm.",
        user_id=u_admin
    )

    print("7. Seeding Realistic Complaints & Executing Workflow...")
    # Complaint 1: Dimensional failure on NDT-800
    res1 = create_complaint(
        reporter_type="Retailer",
        product_id=p_table,
        sku="NDT-800",
        customer_id=c_ikea,
        order_batch_number="LOT-NDT-2026-03",
        category="Dimensional defects",
        description="IKEA warehouse inbound inspection identified assembled table height clearance measured 738 mm, which is below the minimum allowable specification.",
        quantity_affected=15,
        manufacturing_date="2026-02-14",
        severity="High",
        urgency="Urgent",
        assigned_owner_id=u_eng,
        due_date="2026-03-01",
        customer_visible_notes="Report received from IKEA Jönköping Distribution Hub. Quarantine initiated on lot LOT-NDT-2026-03.",
        internal_notes="Suspected CNC leg shortening error during shift 2 on February 12.",
        user_id=u_ikea
    )
    c1_id = res1["id"]
    update_complaint_status(c1_id, "Under Investigation", u_eng, "Engineering investigation and dimensional gauge verification underway.")
    
    # Run evaluation on Complaint 1
    eval_res1 = evaluate_complaint(c1_id, u_eng)
    eval1_id = eval_res1["evaluation_db_id"]
    
    # Risk calculation
    with get_db() as conn:
        c1_dict = dict(conn.execute("SELECT * FROM complaints WHERE id = ?", (c1_id,)).fetchone())
    risk1 = calculate_complaint_risk(c1_dict, eval1_id)
    
    # Root cause hypotheses & CAPA
    hyps1 = generate_root_cause_hypotheses(c1_dict, eval1_id, eval_res1["criteria_results"])
    capas1 = auto_suggest_capas(c1_id, eval1_id, risk1["overall_risk_level"], eval_res1["criteria_results"], u_eng)

    # Complaint 2: Packaging Damage (Transit issue)
    res2 = create_complaint(
        reporter_type="Customer",
        product_id=p_table,
        sku="NDT-800",
        customer_id=c_direct,
        order_batch_number="LOT-NDT-2026-02",
        category="Packaging issues",
        description="Outer shipping carton arrived severely crushed at corner with missing corner protectors. Tabletop has deep 25mm scratch on corner finish.",
        quantity_affected=1,
        manufacturing_date="2026-02-01",
        severity="Medium",
        urgency="Medium",
        assigned_owner_id=u_eng,
        due_date="2026-03-10",
        customer_visible_notes="Replacement tabletop authorized under warranty.",
        internal_notes="Freight carrier claims form submitted.",
        user_id=u_admin
    )
    c2_id = res2["id"]
    update_complaint_status(c2_id, "Triaged", u_eng, "Assigned to logistics team for carrier freight claim.")

    # Complaint 3: Critical Gas Lift Failure on ETC-450 Chair
    res3 = create_complaint(
        reporter_type="Retailer",
        product_id=p_chair,
        sku="ETC-450",
        customer_id=c_target,
        order_batch_number="LOT-ETC-2026-01",
        category="Functional failure",
        description="Target store customer reported Class 4 gas lift cylinder slipping and dropping rapidly from 520mm down to 420mm under normal body weight.",
        quantity_affected=6,
        manufacturing_date="2026-01-20",
        severity="Critical",
        urgency="Urgent",
        assigned_owner_id=u_mgr,
        due_date="2026-02-28",
        customer_visible_notes="Immediate recall notice sent for pallet LOT-ETC-2026-01. Replacement cylinders shipped.",
        internal_notes="Supplier gas cylinder internal seal leakage suspected. Supplier CAR issued.",
        user_id=u_admin
    )
    c3_id = res3["id"]
    eval_res3 = evaluate_complaint(c3_id, u_mgr)
    eval3_id = eval_res3["evaluation_db_id"]
    with get_db() as conn:
        c3_dict = dict(conn.execute("SELECT * FROM complaints WHERE id = ?", (c3_id,)).fetchone())
    risk3 = calculate_complaint_risk(c3_dict, eval3_id)
    hyps3 = generate_root_cause_hypotheses(c3_dict, eval3_id, eval_res3["criteria_results"])
    capas3 = auto_suggest_capas(c3_id, eval3_id, risk3["overall_risk_level"], eval_res3["criteria_results"], u_mgr)
    
    # Manager reviews and signs off on Complaint 3
    review_evaluation(
        evaluation_db_id=eval3_id,
        manager_decision="Escalated",
        manager_notes="Class 4 gas lift failure poses safety hazard. Escalated to VP of Operations and Supplier Quality audit.",
        user_id=u_mgr,
        close_complaint=False
    )

    # Complaint 4: Chemical concern / Moisture warping
    res4 = create_complaint(
        reporter_type="Field Inspector",
        product_id=p_table,
        sku="NDT-800",
        customer_id=c_ikea,
        order_batch_number="LOT-NDT-2026-01",
        category="Material defects",
        description="Tabletop exhibits severe longitudinal warp of 8mm. Digital pin moisture meter reading verified at 16.5% moisture content.",
        quantity_affected=8,
        manufacturing_date="2026-01-18",
        severity="Critical",
        urgency="Urgent",
        assigned_owner_id=u_mgr,
        due_date="2026-02-25",
        customer_visible_notes="Batch held at port quarantine.",
        internal_notes="Kiln drying drying cycle log showed incomplete dwell time during severe winter storm.",
        user_id=u_admin
    )
    c4_id = res4["id"]
    eval_res4 = evaluate_complaint(c4_id, u_mgr)
    eval4_id = eval_res4["evaluation_db_id"]
    with get_db() as conn:
        c4_dict = dict(conn.execute("SELECT * FROM complaints WHERE id = ?", (c4_id,)).fetchone())
    risk4 = calculate_complaint_risk(c4_dict, eval4_id)
    hyps4 = generate_root_cause_hypotheses(c4_dict, eval4_id, eval_res4["criteria_results"])
    capas4 = auto_suggest_capas(c4_id, eval4_id, risk4["overall_risk_level"], eval_res4["criteria_results"], u_mgr)

    # Complaint 5: Closed case with approved evaluation
    res5 = create_complaint(
        reporter_type="Customer",
        product_id=p_cabinet,
        sku="AGC-120",
        customer_id=c_direct,
        order_batch_number="LOT-AGC-2026-01",
        category="Color or finish defects",
        description="Slight paint rubbing on aluminum extrusion corner bracket, length approx 2mm.",
        quantity_affected=1,
        manufacturing_date="2026-01-12",
        severity="Low",
        urgency="Low",
        assigned_owner_id=u_eng,
        user_id=u_admin
    )
    c5_id = res5["id"]
    eval_res5 = evaluate_complaint(c5_id, u_eng)
    eval5_id = eval_res5["evaluation_db_id"]
    with get_db() as conn:
        c5_dict = dict(conn.execute("SELECT * FROM complaints WHERE id = ?", (c5_id,)).fetchone())
    risk5 = calculate_complaint_risk(c5_dict, eval5_id)
    review_evaluation(
        evaluation_db_id=eval5_id,
        manager_decision="Approved",
        manager_notes="Touch-up pen supplied to customer. Defect within acceptable cosmetic limits.",
        user_id=u_mgr,
        close_complaint=True
    )

    print("Demo dataset seeded successfully! All 8 workflows initialized.")

if __name__ == "__main__":
    seed_all_demo_data(reset=True)
