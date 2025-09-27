from ai_model.detect import detect_fake
import time

def submit_to_solana(video_hash, authenticity_score):
    """
    Mock Solana blockchain submission
    In a real implementation, this would connect to your deployed smart contract
    """
    print("🔗 Submitting to Solana blockchain...")
    print(f"📄 Video Hash: {video_hash}")
    print(f"🎯 Authenticity Score: {authenticity_score}")
    print("⛓️  Transaction: [MOCK] Submitted successfully!")
    print("🔐 Data stored immutably on blockchain")
    # TODO: Replace with actual Solana program call when contract is deployed
    return f"tx_{video_hash[:8]}_{int(time.time())}"

def main(video_path):
    print("🚀 Starting SecureAI DeepFake Detection Pipeline")
    print("=" * 50)

    # Step 1: AI Detection
    print("Step 1: AI Analysis")
    detection_result = detect_fake(video_path)

    # Step 2: Blockchain Storage
    print("\nStep 2: Blockchain Storage")
    transaction_id = submit_to_solana(
        detection_result["video_hash"],
        detection_result["authenticity_score"]
    )

    # Step 3: Results Summary
    print("\nStep 3: Final Results")
    print("=" * 50)
    print("📊 DETECTION SUMMARY:")
    print(f"   Video: {video_path}")
    print(f"   Result: {'🚨 DEEPFAKE DETECTED' if detection_result['is_fake'] else '✅ VIDEO AUTHENTIC'}")
    print(f"   Confidence: {detection_result['confidence']:.2%}")
    print(f"   Blockchain TX: {transaction_id}")
    print(f"   Video Hash: {detection_result['video_hash']}")
    print("=" * 50)
    print("✅ Analysis Complete - Results stored securely!")

if __name__ == "__main__":
    # Test with a sample video (you'll need to provide an actual video file)
    main("sample_video.mp4")