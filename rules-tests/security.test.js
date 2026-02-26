const { initializeTestEnvironment, assertFails, assertSucceeds } = require('@firebase/rules-unit-testing');
const { setDoc, getDoc, doc } = require('firebase/firestore');
const fs = require('fs');

let testEnv;

beforeAll(async () => {
    // Load the rules file
    testEnv = await initializeTestEnvironment({
        projectId: 'emektup-staging',
        firestore: {
            rules: fs.readFileSync('../firestore.rules', 'utf8'),
        }
    });
});

afterAll(async () => {
    await testEnv.cleanup();
});

beforeEach(async () => {
    await testEnv.clearFirestore();
});

describe('Firestore Security Rules', () => {

    // 1. DEFAULT POLICY: DENY ALL
    it('should deny unauthorized reads on random collections by default', async () => {
        const unauthedDb = testEnv.unauthenticatedContext().firestore();
        await assertFails(getDoc(doc(unauthedDb, 'somexyz', 'abc')));
    });

    // 2. ORDER_PUBLIC: Guest/Public Read OK, Write DENY
    it('should allow public read on order_public', async () => {
        const unauthedDb = testEnv.unauthenticatedContext().firestore();
        await assertSucceeds(getDoc(doc(unauthedDb, 'order_public', 'TRACK123')));
    });

    it('should deny public write on order_public', async () => {
        const unauthedDb = testEnv.unauthenticatedContext().firestore();
        await assertFails(setDoc(doc(unauthedDb, 'order_public', 'TRACK123'), { status: 'HACKED' }));
    });

    // 3. USERS: User own profile OK
    it('should allow user to read/write their own profile', async () => {
        const authedDb = testEnv.authenticatedContext('user_123', { email: 'user@example.com' }).firestore();
        await assertSucceeds(setDoc(doc(authedDb, 'users', 'user_123'), { name: 'Ahmet' }));
        await assertSucceeds(getDoc(doc(authedDb, 'users', 'user_123')));
    });

    it('should deny user from reading/writing other profiles', async () => {
        const authedDb = testEnv.authenticatedContext('user_123').firestore();
        await assertFails(getDoc(doc(authedDb, 'users', 'user_456')));
        await assertFails(setDoc(doc(authedDb, 'users', 'user_456'), { name: 'Hacked' }));
    });

    // 4. BACKEND-ONLY COLLECTIONS: No frontend access
    it('should deny guest reads on orders', async () => {
        const unauthedDb = testEnv.unauthenticatedContext().firestore();
        await assertFails(getDoc(doc(unauthedDb, 'orders', 'order123')));
    });

    it('should deny guest reads on payments', async () => {
        const unauthedDb = testEnv.unauthenticatedContext().firestore();
        await assertFails(getDoc(doc(unauthedDb, 'payments', 'pay123')));
    });

    it('should deny authenticated user reads on orders', async () => {
        const authedDb = testEnv.authenticatedContext('user_123').firestore();
        await assertFails(getDoc(doc(authedDb, 'orders', 'order123')));
    });
});
