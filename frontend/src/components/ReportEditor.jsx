import React, { useState, useEffect } from 'react';
import { Save, Upload, X } from 'lucide-react';

const ReportEditor = ({ date, report, onSave }) => {
    const [strategy, setStrategy] = useState("");
    const [memo, setMemo] = useState("");
    const [profit, setProfit] = useState("");
    const [profitAmount, setProfitAmount] = useState("");  // 손익 금액 (원)
    const [prevTotalAsset, setPrevTotalAsset] = useState("");  // 전일 총 자산
    const [images, setImages] = useState([]);
    const [newImages, setNewImages] = useState([]);
    const [imagePreviews, setImagePreviews] = useState([]);

    useEffect(() => {
        if (report) {
            setStrategy(report.pre_market_strategy || "");
            setMemo(report.post_market_memo || "");
            setProfit(report.profit_rate || "");
            setProfitAmount(report.profit_amount || "");
            setPrevTotalAsset(report.prev_total_asset || "");
            setImages(report.image_paths || []);
        } else {
            setStrategy(""); setMemo(""); setProfit(""); setProfitAmount(""); setPrevTotalAsset(""); setImages([]);
        }
        setNewImages([]); setImagePreviews([]);
    }, [date, report]);

    const handleImageChange = (e) => {
        if (e.target.files) {
            const files = Array.from(e.target.files);
            setNewImages(prev => [...prev, ...files]);
            const newPreviews = files.map(file => URL.createObjectURL(file));
            setImagePreviews(prev => [...prev, ...newPreviews]);
        }
    };

    const removeNewImage = (idx) => {
        setNewImages(prev => prev.filter((_, i) => i !== idx));
        setImagePreviews(prev => prev.filter((_, i) => i !== idx));
    };

    const removeExistingImage = (idx) => {
        setImages(prev => prev.filter((_, i) => i !== idx));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        const formData = new FormData();
        formData.append('report_date', date);
        formData.append('pre_market_strategy', strategy);
        formData.append('post_market_memo', memo);
        formData.append('profit_rate', profit);
        formData.append('profit_amount', profitAmount);
        formData.append('prev_total_asset', prevTotalAsset);
        formData.append('existing_images', JSON.stringify(images));
        newImages.forEach(file => formData.append('new_images', file));
        await onSave(formData);
    };

    const labelStyle = { display: 'flex', fontSize: '0.9rem', fontWeight: 'bold', marginBottom: '8px', alignItems: 'center', gap: '8px' };
    const inputStyle = { width: '100%', background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(51, 65, 85, 0.6)', borderRadius: '12px', padding: '16px', color: '#e2e8f0', outline: 'none', transition: 'all 0.2s', fontSize: '1rem' };

    return (
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px', height: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'white', display: 'flex', alignItems: 'center', gap: '10px', margin: 0 }}>
                    <div style={{ background: 'rgba(37, 99, 235, 0.2)', padding: '6px', borderRadius: '8px', border: '1px solid rgba(59, 130, 246, 0.3)' }}>📝</div>
                    Report: <span style={{ color: '#60a5fa', fontFamily: 'monospace' }}>{date}</span>
                </h2>
                <button type="submit" style={{
                    display: 'flex', alignItems: 'center', gap: '8px', background: '#2563eb', color: 'white', padding: '10px 20px',
                    borderRadius: '8px', fontWeight: 'bold', border: '1px solid rgba(59, 130, 246, 0.2)', cursor: 'pointer', boxShadow: '0 4px 12px rgba(37, 99, 235, 0.3)'
                }}>
                    <Save size={18} /> Save Report
                </button>
            </div>

            <div className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
                {/* 1. Pre-Market Strategy */}
                <div>
                    <label style={{ ...labelStyle, color: '#34d399' }}>
                        <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981' }}></span>
                        🎯 Pre-Market Strategy
                    </label>
                    <textarea
                        style={{ ...inputStyle, height: '150px', resize: 'none' }}
                        placeholder="Plan your trade logic, scenarios, and risk management..."
                        value={strategy}
                        onChange={e => setStrategy(e.target.value)}
                    />
                </div>

                {/* 2. Post-Market Memo */}
                <div>
                    <label style={{ ...labelStyle, color: '#fbbf24' }}>
                        <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f59e0b' }}></span>
                        📝 Post-Market Feedback
                    </label>
                    <textarea
                        style={{ ...inputStyle, height: '150px', resize: 'none' }}
                        placeholder="Review your execution, psychology, and lessons learned..."
                        value={memo}
                        onChange={e => setMemo(e.target.value)}
                    />
                </div>

                {/* 3. Profit & Images */}
                <div className="responsive-grid-2">
                    <div>
                        <label style={{ ...labelStyle, color: '#60a5fa' }}>💰 전일 수익률 / 손익</label>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                            <div style={{ position: 'relative' }}>
                                <input
                                    type="number" step="0.01"
                                    style={{ ...inputStyle, fontFamily: 'monospace', fontSize: '1.2rem', color: parseFloat(profit) > 0 ? '#f87171' : parseFloat(profit) < 0 ? '#60a5fa' : '#e2e8f0' }}
                                    placeholder="전일 수익률 (%)"
                                    value={profit}
                                    onChange={e => setProfit(e.target.value)}
                                />
                                <span style={{ position: 'absolute', right: '16px', top: '50%', transform: 'translateY(-50%)', color: '#64748b', fontWeight: 'bold' }}>%</span>
                            </div>
                            <div style={{ position: 'relative' }}>
                                <input
                                    type="number"
                                    style={{ ...inputStyle, fontFamily: 'monospace', fontSize: '1.2rem', color: parseFloat(profitAmount) > 0 ? '#f87171' : parseFloat(profitAmount) < 0 ? '#60a5fa' : '#e2e8f0' }}
                                    placeholder="전일 손익 (원)"
                                    value={profitAmount}
                                    onChange={e => setProfitAmount(e.target.value)}
                                />
                                <span style={{ position: 'absolute', right: '14px', top: '50%', transform: 'translateY(-50%)', color: '#64748b', fontSize: '0.8rem' }}>KRW</span>
                            </div>
                        </div>
                    </div>

                    <div>
                        <label style={{ ...labelStyle, color: '#94a3b8' }}>🏦 전일 매도 금액</label>
                        <div style={{ position: 'relative' }}>
                            <input
                                type="number"
                                style={{ ...inputStyle, fontFamily: 'monospace', fontSize: '1.2rem' }}
                                placeholder="총 자산 (원)"
                                value={prevTotalAsset}
                                onChange={e => setPrevTotalAsset(e.target.value)}
                            />
                            <span style={{ position: 'absolute', right: '16px', top: '50%', transform: 'translateY(-50%)', color: '#64748b', fontWeight: 'bold' }}>₩</span>
                        </div>
                    </div>

                    <div>
                        <label style={{ ...labelStyle, color: '#a78bfa' }}>🖼 Attachments</label>
                        <label style={{
                            cursor: 'pointer', background: 'rgba(15, 23, 42, 0.6)', border: '1px dashed #475569', borderRadius: '12px', padding: '12px', display: 'flex',
                            justifyContent: 'center', alignItems: 'center', color: '#94a3b8', height: '58px', transition: 'all 0.2s'
                        }}>
                            <Upload size={18} style={{ marginRight: '8px' }} /> Upload Images
                            <input type="file" multiple accept="image/*" style={{ display: 'none' }} onChange={handleImageChange} />
                        </label>
                    </div>
                </div>

                {/* 4. Image Gallery */}
                {(images.length > 0 || imagePreviews.length > 0) && (
                    <div style={{ display: 'flex', gap: '12px', overflowX: 'auto', padding: '12px', background: 'rgba(2, 6, 23, 0.3)', borderRadius: '12px', border: '1px solid rgba(51, 65, 85, 0.3)' }}>
                        {images.map((img, idx) => (
                            <div key={`exist-${idx}`} style={{ position: 'relative', width: '96px', height: '96px', flexShrink: 0 }}>
                                <img src={img} alt="attached" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '8px', border: '1px solid #334155', cursor: 'pointer' }} onClick={() => window.open(img, '_blank')} />
                                <button type="button" onClick={() => removeExistingImage(idx)} style={{ position: 'absolute', top: '-8px', right: '-8px', background: '#ef4444', color: 'white', border: 'none', borderRadius: '50%', padding: '4px', cursor: 'pointer', boxShadow: '0 2px 4px rgba(0,0,0,0.2)' }}>
                                    <X size={12} />
                                </button>
                            </div>
                        ))}
                        {imagePreviews.map((src, idx) => (
                            <div key={`new-${idx}`} style={{ position: 'relative', width: '96px', height: '96px', flexShrink: 0 }}>
                                <img src={src} alt="preview" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '8px', border: '1px solid #a855f7', opacity: 0.8 }} />
                                <button type="button" onClick={() => removeNewImage(idx)} style={{ position: 'absolute', top: '-8px', right: '-8px', background: '#ef4444', color: 'white', border: 'none', borderRadius: '50%', padding: '4px', cursor: 'pointer', boxShadow: '0 2px 4px rgba(0,0,0,0.2)' }}>
                                    <X size={12} />
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </form>
    );
};

export default ReportEditor;
