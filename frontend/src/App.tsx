import React, { useState } from 'react';
import { Upload, FileText, CheckCircle, AlertTriangle, Loader2, Download } from 'lucide-react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';

// Define types
interface AnalysisResponse {
    success: boolean;
    report_md: string;
    report_json: any;
    filename: string;
}

function App() {
    const [file, setFile] = useState<File | null>(null);
    const [isUploading, setIsUploading] = useState(false);
    const [report, setReport] = useState<AnalysisResponse | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setError(null);
        }
    };

    const handleUpload = async () => {
        if (!file) return;

        setIsUploading(true);
        setError(null);

        const formData = new FormData();
        formData.append('inspection_file', file);

        try {
            // Use proxy configured in vite.config.ts
            const response = await axios.post('/api/analyze', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            setReport(response.data);
        } catch (err: any) {
            console.error(err);
            setError(err.response?.data?.detail || 'Analysis failed. Please try again.');
        } finally {
            setIsUploading(false);
        }
    };

    const downloadReport = () => {
        if (!report) return;
        const blob = new Blob([report.report_md], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = report.filename || 'report.md';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    return (
        <div className="min-h-screen p-8 max-w-5xl mx-auto">
            <header className="mb-10 text-center">
                <h1 className="text-4xl font-bold text-slate-800 mb-2">DDR Generator</h1>
                <p className="text-slate-500">Upload your inspection PDF to generate a comprehensive diagnostic report</p>
            </header>

            {!report ? (
                <div className="max-w-xl mx-auto bg-white rounded-xl shadow-sm border border-slate-200 p-8">
                    <div className="border-2 border-dashed border-slate-300 rounded-lg p-12 text-center hover:bg-slate-50 transition-colors">
                        <input
                            type="file"
                            accept=".pdf"
                            onChange={handleFileChange}
                            className="hidden"
                            id="file-upload"
                        />
                        <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center">
                            <Upload className="w-12 h-12 text-blue-500 mb-4" />
                            <span className="text-lg font-medium text-slate-700">
                                {file ? file.name : "Click to upload PDF"}
                            </span>
                            <span className="text-sm text-slate-400 mt-2">Maximum file size: 10MB</span>
                        </label>
                    </div>

                    {error && (
                        <div className="mt-4 p-4 bg-red-50 text-red-700 rounded-lg flex items-start gap-3">
                            <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
                            <p>{error}</p>
                        </div>
                    )}

                    <button
                        onClick={handleUpload}
                        disabled={!file || isUploading}
                        className="w-full mt-6 bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-lg flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    >
                        {isUploading ? (
                            <>
                                <Loader2 className="w-5 h-5 animate-spin" />
                                Processing Report...
                            </>
                        ) : (
                            <>
                                <FileText className="w-5 h-5" />
                                Generate Report
                            </>
                        )}
                    </button>

                    {isUploading && (
                        <p className="text-center text-sm text-slate-400 mt-4 animate-pulse">
                            Running Groq AI Analysis... This may take up to 2 minutes.
                        </p>
                    )}
                </div>
            ) : (
                <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                    <div className="bg-slate-50 border-b border-slate-200 p-4 flex justify-between items-center sticky top-0 z-10">
                        <div className="flex items-center gap-3">
                            <div className="bg-green-100 p-2 rounded-full">
                                <CheckCircle className="w-5 h-5 text-green-600" />
                            </div>
                            <div>
                                <h2 className="font-semibold text-slate-800">Analysis Complete</h2>
                                <p className="text-xs text-slate-500">{report.filename}</p>
                            </div>
                        </div>
                        <div className="flex gap-3">
                            <button
                                onClick={() => setReport(null)}
                                className="text-slate-600 hover:text-slate-800 font-medium text-sm px-3 py-2"
                            >
                                Upload New
                            </button>
                            <button
                                onClick={downloadReport}
                                className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg flex items-center gap-2"
                            >
                                <Download className="w-4 h-4" />
                                Download Markdown
                            </button>
                        </div>
                    </div>

                    <div className="p-8 prose prose-slate max-w-none">
                        <ReactMarkdown>{report.report_md}</ReactMarkdown>
                    </div>
                </div>
            )}
        </div>
    );
}

export default App;
