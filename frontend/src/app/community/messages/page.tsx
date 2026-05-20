import { redirect } from 'next/navigation';

export default function RedirectToInboxMessages() {
    redirect('/inbox/messages');
}
