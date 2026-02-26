import { Link } from "react-router-dom";

export default function Home() {
    return (
        <div className="min-h-screen flex flex-col items-center justify-center p-4">
            <div className="max-w-md text-center space-y-6">
                <h1 className="text-4xl font-bold text-gray-900">Emektup'a Hoş Geldiniz</h1>
                <p className="text-lg text-gray-600">
                    Sevdiklerinize cezaevine kolayca ve güvenle mektup gönderin. Vakit kaybetmeden hemen yazmaya başlayın.
                </p>
                <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
                    <Link
                        to="/write"
                        className="px-6 py-3 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-500 transition-colors"
                    >
                        Hemen Mektup Yaz
                    </Link>
                    <Link
                        to="/track"
                        className="px-6 py-3 bg-white text-gray-700 border border-gray-300 font-medium rounded-lg hover:bg-gray-50 transition-colors"
                    >
                        Mektup Takibi
                    </Link>
                </div>
            </div>
        </div>
    );
}
