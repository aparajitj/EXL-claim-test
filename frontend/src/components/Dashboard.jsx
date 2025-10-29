import { useState, useEffect } from "react";
import axios from "axios";
import { API } from "../App";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { Upload, FileText, LogOut, History, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";

const Dashboard = ({ user, onLogout }) => {
  const [files, setFiles] = useState({
    policy: null,
    claim: null,
    bills: null,
    doctor_notes: null,
  });
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const response = await axios.get(`${API}/claims/history`);
      setHistory(response.data);
    } catch (error) {
      console.error("Error fetching history:", error);
    }
  };

  const handleFileChange = (type, e) => {
    const file = e.target.files[0];
    if (file && file.type === "application/pdf") {
      setFiles({ ...files, [type]: file });
    } else {
      toast.error("Please upload a PDF file");
    }
  };

  const handleAnalyze = async () => {
    if (!files.policy || !files.claim || !files.bills || !files.doctor_notes) {
      toast.error("Please upload all required documents");
      return;
    }

    setAnalyzing(true);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("policy", files.policy);
      formData.append("claim", files.claim);
      formData.append("bills", files.bills);
      formData.append("doctor_notes", files.doctor_notes);

      const response = await axios.post(`${API}/claims/analyze`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setResult(response.data);
      toast.success("Analysis complete!");
      fetchHistory();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Analysis failed. Please try again.");
    } finally {
      setAnalyzing(false);
    }
  };

  const FileUploadCard = ({ title, type, icon: Icon }) => (
    <Card className="hover:shadow-md transition-shadow cursor-pointer" style={{ borderColor: files[type] ? '#0369a1' : '#e5e7eb' }}>
      <CardContent className="p-6">
        <label htmlFor={`file-${type}`} className="cursor-pointer block">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl" style={{ backgroundColor: files[type] ? '#bae6fd' : '#f3f4f6' }}>
              <Icon className="w-6 h-6" style={{ color: files[type] ? '#0369a1' : '#6b7280' }} />
            </div>
            <div className="flex-1">
              <p className="font-medium text-base mb-1">{title}</p>
              <p className="text-sm text-gray-500">
                {files[type] ? files[type].name : "Click to upload PDF"}
              </p>
            </div>
            {files[type] && (
              <CheckCircle2 className="w-5 h-5" style={{ color: '#0369a1' }} />
            )}
          </div>
        </label>
        <input
          id={`file-${type}`}
          data-testid={`upload-${type}-input`}
          type="file"
          accept="application/pdf"
          onChange={(e) => handleFileChange(type, e)}
          className="hidden"
        />
      </CardContent>
    </Card>
  );

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(135deg, #e0f2fe 0%, #f0f9ff 100%)' }}>
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-10" style={{ borderColor: '#cbd5e1' }}>
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: '#0369a1' }}>
              ClaimGuard AI
            </h1>
            <p className="text-sm text-gray-600">Welcome, {user.full_name}</p>
          </div>
          <div className="flex gap-3">
            <Button
              data-testid="view-history-button"
              variant="outline"
              onClick={() => setShowHistory(!showHistory)}
              className="gap-2"
            >
              <History className="w-4 h-4" />
              {showHistory ? "Hide History" : "View History"}
            </Button>
            <Button
              data-testid="logout-button"
              variant="outline"
              onClick={onLogout}
              className="gap-2"
              style={{ borderColor: '#ef4444', color: '#ef4444' }}
            >
              <LogOut className="w-4 h-4" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {!showHistory ? (
          <>
            {/* Upload Section */}
            <Card className="mb-8 border-0 shadow-lg">
              <CardHeader>
                <CardTitle className="text-2xl" style={{ color: '#0c4a6e' }}>Upload Documents</CardTitle>
                <CardDescription className="text-base">
                  Upload all required documents for AI analysis
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid md:grid-cols-2 gap-4">
                  <FileUploadCard title="Insurance Policy" type="policy" icon={FileText} />
                  <FileUploadCard title="Claim Form" type="claim" icon={FileText} />
                  <FileUploadCard title="Medical Bills" type="bills" icon={FileText} />
                  <FileUploadCard title="Doctor Notes" type="doctor_notes" icon={FileText} />
                </div>
                <Button
                  data-testid="analyze-claim-button"
                  onClick={handleAnalyze}
                  disabled={analyzing}
                  className="w-full h-12 text-base font-medium gap-2"
                  style={{ backgroundColor: '#0369a1' }}
                >
                  {analyzing ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Analyzing Documents...
                    </>
                  ) : (
                    <>
                      <Upload className="w-5 h-5" />
                      Analyze Claim
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>

            {/* Result Section */}
            {result && (
              <Card className="border-0 shadow-lg" data-testid="analysis-result">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-2xl" style={{ color: '#0c4a6e' }}>Analysis Result</CardTitle>
                    <Badge
                      data-testid="decision-badge"
                      className="text-lg px-4 py-2"
                      style={{
                        backgroundColor: result.decision === "PASS" ? '#22c55e' : '#ef4444',
                        color: 'white'
                      }}
                    >
                      {result.decision === "PASS" ? (
                        <CheckCircle2 className="w-5 h-5 mr-2 inline" />
                      ) : (
                        <XCircle className="w-5 h-5 mr-2 inline" />
                      )}
                      {result.decision}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <h3 className="font-semibold text-lg mb-2" style={{ color: '#0c4a6e' }}>Reasoning:</h3>
                    <p className="text-gray-700 leading-relaxed whitespace-pre-wrap" data-testid="reasoning-text">{result.reasoning}</p>
                  </div>
                  {result.confidence_score && (
                    <div>
                      <h3 className="font-semibold text-lg mb-2" style={{ color: '#0c4a6e' }}>Confidence Score:</h3>
                      <div className="flex items-center gap-3">
                        <div className="flex-1 h-3 bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${result.confidence_score}%`,
                              backgroundColor: '#0369a1'
                            }}
                          />
                        </div>
                        <span className="font-medium" style={{ color: '#0369a1' }}>{result.confidence_score}%</span>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </>
        ) : (
          /* History Section */
          <Card className="border-0 shadow-lg">
            <CardHeader>
              <CardTitle className="text-2xl" style={{ color: '#0c4a6e' }}>Analysis History</CardTitle>
              <CardDescription className="text-base">
                View your previous claim analyses
              </CardDescription>
            </CardHeader>
            <CardContent>
              {history.length === 0 ? (
                <p className="text-center text-gray-500 py-8">No analysis history yet</p>
              ) : (
                <div className="space-y-4" data-testid="history-list">
                  {history.map((item) => (
                    <Card key={item.id} className="hover:shadow-md transition-shadow">
                      <CardContent className="p-6">
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex-1">
                            <p className="text-sm text-gray-500 mb-2">
                              {new Date(item.analyzed_at).toLocaleString()}
                            </p>
                            <div className="flex flex-wrap gap-2 text-sm text-gray-600">
                              <span>Policy: {item.policy_file}</span>
                              <span>•</span>
                              <span>Claim: {item.claim_file}</span>
                            </div>
                          </div>
                          <Badge
                            style={{
                              backgroundColor: item.decision === "PASS" ? '#22c55e' : '#ef4444',
                              color: 'white'
                            }}
                          >
                            {item.decision}
                          </Badge>
                        </div>
                        <p className="text-gray-700 line-clamp-2">{item.reasoning}</p>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default Dashboard;