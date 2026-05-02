import { SpeakersPanel } from '@/components/meeting/speakers/speakers-panel';
import { meeting, people } from '@/lib/mock';

const SpeakersPage = () => <SpeakersPanel meeting={meeting} people={people} />;

export default SpeakersPage;
