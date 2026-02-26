import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { endpoints } from "../lib/api";

export default function Tracker() {
    const { code } = useParams<{ code?: string }>();
    const navigate = useNavigate();
    const [inputCode, setInputCode] = useState(code || "");

    const { data, isPending, isError, error } = useQuery({
        queryKey: ["order", "track", code],
        queryFn: () => endpoints.trackOrder(code!),
        enabled: !!code, // Only fetch if code exists in URL
        retry: false // Fail fast on 404s
    });

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        if (inputCode.trim()) {
            navigate(`/track/${inputCode.trim()}`);
        }
    };

    return (
        <div className="max-w-xl mx-auto p-4 py-8">
            <h1 className="text-2xl font-bold mb-6 text-slate-800 text-center">Mektup Takibi</h1>

            <form onSubmit={handleSearch} className="flex gap-2 mb-8 items-center bg-white p-2 rounded-lg shadow-sm border border-slate-200">
                <input
                    type="text"
                    value={inputCode}
                    onChange={(e) => setInputCode(e.target.value)}
                    placeholder="Takip kodunuzu girin"
                    className="flex-1 p-3 outline-none"
                />
                <button type="submit" className="px-6 py-3 bg-primary-600 text-white rounded-md hover:bg-primary-500 transition-colors font-medium">
                    Sorgula
                </button>
            </form>

            {/* Loading state */}
            {isPending && !!code && (
                <div className="text-center py-12 text-slate-500">
                    <div className="animate-spin w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full mx-auto mb-4"></div>
                    Sipariş durumu sorgulanıyor...
                </div>
            )}

            {/* Error state */}
            {isError && !!code && (
                <div className="bg-red-50 border border-red-200 text-red-600 p-6 rounded-xl text-center">
                    Sipariş bulunamadı veya bir hata oluştu:
                    <br />
                    <span className="font-semibold">{((error as any)?.message) || "Geçersiz takip kodu"}</span>
                </div>
            )}

            {/* Data display */}
            {data && (
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 space-y-4">
                    <div className="border-b pb-4 flex justify-between items-center">
                        <div>
                            <p className="text-sm text-slate-500">Takip Kodu</p>
                            <p className="font-mono font-medium text-slate-900">{code}</p>
                        </div>
                        <div className="text-right">
                            <p className="text-sm text-slate-500">Durum</p>
                            <span className="inline-flex items-center rounded-md bg-blue-50 px-2.5 py-1 text-sm font-medium text-blue-700 ring-1 ring-inset ring-blue-700/10">
                                {data.status}
                            </span>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <p className="text-sm text-slate-500">Alıcı</p>
                            <p className="font-medium text-slate-900">{data.recipient_name || "Belirtilmedi"}</p>
                        </div>
                        <div>
                            <p className="text-sm text-slate-500">Cezaevi</p>
                            <p className="font-medium text-slate-900">{data.prison_name || "Belirtilmedi"}</p>
                        </div>
                        <div>
                            <p className="text-sm text-slate-500">Oluşturulma Tarihi</p>
                            <p className="font-medium text-slate-900">
                                {new Date(data.created_at).toLocaleString('tr-TR')}
                            </p>
                        </div>
                        {data.label && (
                            <div>
                                <p className="text-sm text-slate-500">Kargo/Takip Etiketi</p>
                                <p className="font-medium text-slate-900">{data.label}</p>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
