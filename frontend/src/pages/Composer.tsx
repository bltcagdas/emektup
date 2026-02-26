import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { endpoints, CreateOrderPayload } from "../lib/api";

const LetterCreateSchema = z.object({
    letter_text: z.string().min(10, "Mektup metni çok kısa").max(20000, "Mektup çok uzun"),
    recipient_name: z.string().optional(),
    prison_name: z.string().min(3, "Cezaevi adı gereklidir"),
    city: z.string().min(2, "Şehir adı gereklidir"),
    address_line: z.string().min(5, "Adres gereklidir").max(150, "Adres çok uzun"),
    sender_name: z.string().optional(),
    sender_city: z.string().optional(),
});

type LetterFormValues = z.infer<typeof LetterCreateSchema>;

export default function Composer() {
    const navigate = useNavigate();

    const {
        register,
        handleSubmit,
        formState: { errors }
    } = useForm<LetterFormValues>({
        resolver: zodResolver(LetterCreateSchema),
        defaultValues: {
            letter_text: "",
            prison_name: "",
            city: "",
            address_line: "",
            recipient_name: "",
            sender_name: "",
            sender_city: ""
        }
    });

    const createOrderMutation = useMutation({
        mutationFn: (data: CreateOrderPayload) => endpoints.createOrder(data),
        onSuccess: (data) => {
            // Form sent successfully
            localStorage.setItem("emektup:last_order", JSON.stringify({
                order_id: data.order_id,
                tracking_code: data.tracking_code
            }));

            // Navigate to checkout
            navigate(`/checkout/${data.order_id}?code=${data.tracking_code}`);
        }
    });

    const onSubmit = (data: LetterFormValues) => {
        createOrderMutation.mutate(data);
    };

    return (
        <div className="max-w-3xl mx-auto p-4 py-8">
            <h1 className="text-2xl font-bold mb-6 text-slate-800">Yeni Mektup Yaz</h1>

            {createOrderMutation.isError && (
                <div className="mb-6 p-4 bg-red-50 text-red-600 rounded-lg border border-red-200">
                    Sipariş oluşturulamadı. Lütfen tekrar deneyin. (
                    {(createOrderMutation.error as any)?.message || "Bilinmeyen hata"}
                    )
                </div>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 bg-white p-6 rounded-xl shadow-sm border border-slate-200">

                <div className="space-y-4">
                    <h2 className="text-lg font-semibold text-slate-700 border-b pb-2">Alıcı Bilgileri</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Alıcı Adı Soyadı (Opsiyonel)</label>
                            <input {...register("recipient_name")} className="w-full p-2 border border-slate-300 rounded-md focus:ring-primary-500 focus:border-primary-500" placeholder="Örn: Ahmet Yılmaz" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Cezaevi Adı *</label>
                            <input {...register("prison_name")} className="w-full p-2 border border-slate-300 rounded-md focus:ring-primary-500 focus:border-primary-500" placeholder="Örn: Silivri Kapalı Cezaevi" />
                            {errors.prison_name && <p className="text-red-500 text-sm mt-1">{errors.prison_name.message}</p>}
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Şehir *</label>
                            <input {...register("city")} className="w-full p-2 border border-slate-300 rounded-md focus:ring-primary-500 focus:border-primary-500" placeholder="Örn: İstanbul" />
                            {errors.city && <p className="text-red-500 text-sm mt-1">{errors.city.message}</p>}
                        </div>
                        <div className="md:col-span-2">
                            <label className="block text-sm font-medium text-slate-700 mb-1">Tam Adres / Koğuş *</label>
                            <input {...register("address_line")} className="w-full p-2 border border-slate-300 rounded-md focus:ring-primary-500 focus:border-primary-500" placeholder="C-3 Koğuşu, Posta kutusu vb." />
                            {errors.address_line && <p className="text-red-500 text-sm mt-1">{errors.address_line.message}</p>}
                        </div>
                    </div>
                </div>

                <div className="space-y-4 pt-4">
                    <h2 className="text-lg font-semibold text-slate-700 border-b pb-2">Mektup İçeriği *</h2>
                    <div>
                        <textarea
                            {...register("letter_text")}
                            className="w-full p-3 border border-slate-300 rounded-md min-h-[300px] focus:ring-primary-500 focus:border-primary-500"
                            placeholder="Mektubunuzu buraya yazın..."
                        />
                        {errors.letter_text && <p className="text-red-500 text-sm mt-1">{errors.letter_text.message}</p>}
                    </div>
                </div>

                <div className="space-y-4 pt-4">
                    <h2 className="text-lg font-semibold text-slate-700 border-b pb-2">Gönderen Bilgileri (Opsiyonel)</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Adınız Soyadınız</label>
                            <input {...register("sender_name")} className="w-full p-2 border border-slate-300 rounded-md focus:ring-primary-500 focus:border-primary-500" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Bulunduğunuz Şehir</label>
                            <input {...register("sender_city")} className="w-full p-2 border border-slate-300 rounded-md focus:ring-primary-500 focus:border-primary-500" />
                        </div>
                    </div>
                </div>

                <div className="pt-6 border-t flex items-center justify-end">
                    <button
                        type="submit"
                        disabled={createOrderMutation.isPending}
                        className="px-8 py-3 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        {createOrderMutation.isPending ? "Oluşturuluyor..." : "Siparişi Oluştur ve Ödemeye Geç"}
                    </button>
                </div>
            </form>
        </div>
    );
}
