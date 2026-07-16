import { ExtensionPopup } from '@/components/extension/extension-popup';
import { people } from '@/lib/mock/people';

// TODO(api): participant/auth API is not available to the extension popup.
const ExtensionPage = () => <ExtensionPopup people={people} />;

export default ExtensionPage;
