import { useParams, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { endpoints } from "../lib/api";

export default function Checkout() {
    const { orderId } = useParams<{ orderId: string }>();
    const navigate = useNavigate();

    const intentMutation = useMutation({
        mutationFn: (id: string) => endpoints.createPaymentIntent(id),
        onSuccess: (data) => {
            // Redirect to the payment provider URL
            window.location.href = data.checkout_url;
        }
    });

    const handlePayment = () => {
        if (orderId) {
            intentMutation.mutate(orderId);
        }
    };

    return (
        <div className="max-w-md mx-auto p-4 py-12 text-center">
            <div className="bg-white p-8 rounded-xl shadow-sm border border-slate-200">
                <h1 className="text-2xl font-bold mb-4 text-slate-800">Ödeme Adımı</h1>
                <p className="text-slate-600 mb-8">
                    Siparişiniz (<span className="font-mono text-sm">{orderId}</span>) oluşturuldu. Ödeme sağlayıcısına yönlendiriliyorsunuz.
                </p>

                {intentMutation.isError && (
                    <div className="mb-6 p-4 bg-red-50 text-red-600 rounded-lg text-sm border border-red-200">
                        Ödeme başlatılamadı: {((intentMutation.error as any)?.message) || "Bilinmeyen Hata"}
                    </div>
                )}

                <button
                    onClick={handlePayment}
                    disabled={intentMutation.isPending}
                    className="px-6 py-3 bg-primary-600 text-white font-medium rounded-lg w-full hover:bg-primary-500 disabled:opacity-50 transition-colors"
                >
                    {intentMutation.isPending ? "Yönlendiriliyor..." : "Güvenli Ödeme Yap"}
                </button>

                <div className="mt-4">
                    <button onClick={() => navigate(-1)} className="text-sm text-slate-500 hover:text-slate-800 underline">Geri Dön</button>
                </div>
            </div>
        </div>
    );
}
