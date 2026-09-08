import { I18nProvider } from "./i18n";
import WorkspacePage from "./pages/WorkspacePage";

export default function App() {
  return (
    <I18nProvider>
      <WorkspacePage />
    </I18nProvider>
  );
}
