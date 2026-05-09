import { BrowserRouter, Route, Routes } from "react-router-dom";

import { RequireAuth } from "./components/RequireAuth";
import { AppShell } from "./layouts/AppShell";
import { CandidateLogin } from "./pages/auth/CandidateLogin";
import { CandidateRegister } from "./pages/auth/CandidateRegister";
import { HrLogin } from "./pages/auth/HrLogin";
import { HrRegister } from "./pages/auth/HrRegister";
import { CandidateChat } from "./pages/candidate/Chat";
import { CareerGuide } from "./pages/candidate/CareerGuide";
import { CandidateDashboard } from "./pages/candidate/Dashboard";
import { CandidateInterview } from "./pages/candidate/Interview";
import { CandidateInterviews } from "./pages/candidate/Interviews";
import { InterviewReport } from "./pages/candidate/InterviewReport";
import { CandidateJobs } from "./pages/candidate/Jobs";
import { CandidateJobDetail } from "./pages/candidate/JobDetail";
import { MockInterview } from "./pages/candidate/MockInterview";
import { CandidateNotifications } from "./pages/candidate/Notifications";
import { CandidateResumes } from "./pages/candidate/Resumes";
import { HrApplicants } from "./pages/hr/Applicants";
import { HrChat } from "./pages/hr/Chat";
import { HrDashboard } from "./pages/hr/Dashboard";
import { HrJobs } from "./pages/hr/Jobs";
import { HrNotifications } from "./pages/hr/Notifications";
import { HrPostJob } from "./pages/hr/PostJob";
import { Forbidden } from "./pages/Forbidden";
import { Landing } from "./pages/Landing";
import { NotFound } from "./pages/NotFound";

function App() {
  return (
    <BrowserRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/forbidden" element={<Forbidden />} />

        <Route path="/candidate/login" element={<CandidateLogin />} />
        <Route path="/candidate/register" element={<CandidateRegister />} />
        <Route
          path="/candidate"
          element={
            <RequireAuth role="candidate">
              <AppShell role="candidate" />
            </RequireAuth>
          }
        >
          <Route path="dashboard" element={<CandidateDashboard />} />
          <Route path="resume" element={<CandidateResumes />} />
          <Route path="jobs" element={<CandidateJobs />} />
          <Route path="jobs/:jobId" element={<CandidateJobDetail />} />
          <Route path="interviews" element={<CandidateInterviews />} />
          <Route path="interview/:applicationId" element={<CandidateInterview />} />
          <Route path="interview/:interviewId/report" element={<InterviewReport />} />
          <Route path="mock-interview" element={<MockInterview />} />
          <Route path="notifications" element={<CandidateNotifications />} />
          <Route path="chat" element={<CandidateChat />} />
          <Route path="career-guide" element={<CareerGuide />} />
        </Route>

        <Route path="/hr/login" element={<HrLogin />} />
        <Route path="/hr/register" element={<HrRegister />} />
        <Route
          path="/hr"
          element={
            <RequireAuth role="hr">
              <AppShell role="hr" />
            </RequireAuth>
          }
        >
          <Route path="dashboard" element={<HrDashboard />} />
          <Route path="post-job" element={<HrPostJob />} />
          <Route path="jobs" element={<HrJobs />} />
          <Route path="job/:jobId/applicants" element={<HrApplicants />} />
          <Route path="notifications" element={<HrNotifications />} />
          <Route path="chat" element={<HrChat />} />
        </Route>

        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
