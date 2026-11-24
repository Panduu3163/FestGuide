import { DemoSplitView } from "./views/DemoSplitView";
import { OrganizerConsole } from "./views/OrganizerConsole";
import { StudentWorkspace } from "./views/StudentWorkspace";

export function App() {
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
  const framed = window.self !== window.top;

  if (path === "/organizer") {
    return <OrganizerConsole framed={framed} />;
  }
  if (path === "/demo") {
    return <DemoSplitView />;
  }
  return <StudentWorkspace framed={framed} />;
}

export default App;
