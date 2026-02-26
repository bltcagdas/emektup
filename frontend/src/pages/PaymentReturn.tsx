import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";
import { endpoints } from "../lib/api";

export default function PaymentReturn() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const [orderDetails, setOrderDetails] = useState<{ order_id: string, tracking_code: string } | null>(null);

    // Parse order ID / tracking directly or from local storage fallback
    useEffect(() => {
        // Usually Iyzico returns a token or orderId via POST or GET
        // For MVP thin-slice, we fallback to our local storage
        const raw = localStorage.getItem("emektup:last_order");
        const parsed = raw ? JSON.parse(raw) : null;

        // Example: If gateway appends orderId parameter (e.g., ?orderId=123)
        const urlOrderId = searchParams.get("orderId");

        if (parsed) {
            setOrderDetails(parsed);
        } else if (urlOrderId) {
            setOrderDetails({ order_id: urlOrderId, tracking_code: "" });
        }
    }, [searchParams]);

    // Polling mechanism
    const { data, isError, error } = useQuery({
        queryKey: ["payment", "status", orderDetails?.order_id],
        queryFn: () => endpoints.getPaymentStatus(orderDetails!.order_id),
        enabled: !!orderDetails?.order_id,
        refetchInterval: (query) => {
            // Stop polling if PAID or FAILED
            if (query.state.data?.payment_status === "PAID" || query.state.data?.payment_status === "FAILED") {
                return false;
            }
            return 4000; // Poll every 4s to prevent 429 Too Many Requests
        },
        staleTime: 0 // Always fetch fresh
    });

    if (!orderDetails) {
        return (
            <div className="max-w-md mx-auto p-4 py-12 text-center text-slate-600">
                Sipariş bulunamadı. Lütfen anasayfaya dönün.
            </div>
        );
    }

    const status = data?.payment_status || "PENDING";

    return (
        <div className="max-w-md mx-auto p-4 py-12 text-center">
            <div className="bg-white p-8 rounded-xl shadow-sm border border-slate-200">

                {status === "PENDING" && (
                    <>
                        <h1 className="text-2xl font-bold mb-4 text-slate-800">Ödeme Durumu</h1>
                        <div className="animate-pulse flex space-x-4 items-center justify-center my-8">
                            <div className="rounded-full bg-slate-300 h-10 w-10"></div>
                            <div className="flex-1 space-y-4 py-1">
                                <div className="h-4 bg-slate-300 rounded w-3/4 mx-auto"></div>
                                <div className="h-4 bg-slate-300 rounded w-1/2 mx-auto"></div>
                            </div>
                        </div>
                        <p className="text-slate-600">Ödemeniz doğrulanıyor, lütfen bekleyin...</p>
                    </>
                )}

                {status === "PAID" && (
                    <>
                        <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-4 text-3xl">✓</div>
                        <h1 className="text-2xl font-bold mb-4 text-slate-800">Ödeme Onaylandı!</h1>
                        <p className="text-slate-600 mb-8">Mektubunuz baskıya alındı.</p>
                        <button
                            onClick={() => navigate(`/track/${orderDetails.tracking_code}`)}
                            className="px-6 py-3 bg-primary-600 text-white font-medium rounded-lg w-full hover:bg-primary-500 transition-colors"
                        >
                            Sipariş Takibi
                        </button>
                    </>
                )}

                {status === "FAILED" && (
                    <>
                        <div className="w-16 h-16 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto mb-4 text-3xl">✕</div>
                        <h1 className="text-2xl font-bold mb-4 text-slate-800">Ödeme Başarısız</h1>
                        <p className="text-slate-600 mb-8">İşleminiz sırasında bir sorun oluştu.</p>
                        <button
                            onClick={() => navigate(`/checkout/${orderDetails.order_id}`)}
                            className="px-6 py-3 bg-white text-slate-700 font-medium rounded-lg border border-slate-300 w-full hover:bg-slate-50 transition-colors"
                        >
                            Tekrar Dene
                        </button>
                    </>
                )}

                {isError && (
                    <div className="mt-6 p-4 bg-red-50 text-red-600 rounded-lg text-sm border border-red-200">
                        Sorgulama hatası: {((error as any)?.message) || "Sunucuya ulaşılamıyor."}
                    </div>
                )}

            </div>
        </div>
    );
}
