from app.collectors.local_document_extractor import LocalDocumentExtractor

def test_local():
    print("Testing 100% Free Local Document Extractor...")
    extractor = LocalDocumentExtractor()
    
    sample_text = """
    GOVERNMENT OF ODISHA
    OFFICE OF THE COLLECTOR, KHORDHA
    Tender Notice No: 05/2026-27
    Name of Work: Supply of Smart Interactive Panels for Schools.
    Estimated Cost: Rs. 15,00,000/-
    Earnest Money Deposit (EMD): Rs. 30,000/-
    Last Date of Submission: 30-08-2026
    Delivery Location: District Education Office, Khordha, Odisha.
    """
    
    result = extractor.extract_tender_details(sample_text, source="District")
    print("\nLocal Extraction Result:")
    for k, v in result.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    test_local()