"""Start the platform:  python run.py   (API + built frontend on http://localhost:5000)"""
import os

from app import create_app, init_platform, start_scheduler

app = create_app()

if __name__ == "__main__":
    init_platform(app)
    start_scheduler(app)
    from app.services.otp import mail_status
    with app.app_context():
        print("\n  " + mail_status())
    port = int(os.getenv("PORT", "5000"))
    print(f"\n  🏙️  AI Smart City Intelligence Platform → http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
