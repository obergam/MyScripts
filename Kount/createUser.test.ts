import { PfeRoutes } from "@kount/yodalib_ui_cypress_8/dist/pfe/portal/pfeRoutes";
import { AdminPageActions } from "@kount/yodalib_ui_cypress_8/dist/pfe/portal/ui/actions/adminPageActions";
import { CreateUserPageActions } from "@kount/yodalib_ui_cypress_8/dist/pfe/portal/ui/actions/createUserPageAction";
import { UnsavedChangeModalActions } from "@kount/yodalib_ui_cypress_8/dist/pfe/portal/ui/actions/unsavedChangeModalActions";
import "cypress-xpath";
import * as faker from "faker";
import * as randomatic from "randomatic";
import * as clientMessage from "../../../fixtures/messages/clientManagementMessage.json";
import * as modalMessage from "../../../fixtures/messages/modalMessages.json";
import * as createUsersDetails from "../../../fixtures/users/createUsers.json";
import { ClientManagementHelper } from "../../../helpers/clientManagementHelper";
import { IdentityHelper } from "../../../helpers/identity/identityHelper";
import { LoginHelper } from "../../../helpers/loginHelper";
import { TestHelper } from "../../../src/TestHelper";

describe("Portal Create User Page", () => {
    let env: any;
    let randomFirstName: string;
    let randomLastName: string;
    let randomEmail: string;
    let emailsUsed: string[];
    let adminPage: AdminPageActions;
    let createUserPage: CreateUserPageActions;
    let loginHelper: LoginHelper;
    let clientManagementHelper: ClientManagementHelper;
    let unsavedChangesModel: UnsavedChangeModalActions;
    let identityHelper: IdentityHelper;
    let pfeRoutes: PfeRoutes;
    const nameCharLimit: number = 50;
    const maxLengthFirstName: string = randomatic("Aa", nameCharLimit);
    const maxLengthEmail: string = "auto_" + faker.random.alphaNumeric(59) + "@" + faker.random.alphaNumeric(31) + ".com";
    const randomPhoneNumber: string = faker.random.number({ min: 1000000000, max: 9999999999 }).toString();
    const maxLengthLastName: string = randomatic("Aa", nameCharLimit);
    const invalidPhoneNumber: string = faker.random.number({ min: 100000, max: 999999 }).toString() + randomPhoneNumber;

    before("Define Variables and Login into Portal", () => {
        env = new TestHelper().parseEnv(Cypress.env());
        adminPage = AdminPageActions.fromCypressEnv(env);
        createUserPage = CreateUserPageActions.fromCypressEnv(env);
        clientManagementHelper = new ClientManagementHelper();
        identityHelper = new IdentityHelper();
        loginHelper = new LoginHelper();
        unsavedChangesModel = new UnsavedChangeModalActions();
        pfeRoutes = new PfeRoutes();
        loginHelper.login(createUsersDetails.email);
        emailsUsed = [];
    });

    beforeEach("Navigating to Create User Page", () => {
        loginHelper.preserveStorage();
        clientManagementHelper.navigateToAdminPage();
        clientManagementHelper.navigateToCreateUser();
        randomFirstName = faker.name.firstName();
        randomLastName = faker.name.lastName();
        randomEmail = "auto_" + faker.random.alphaNumeric(6) + faker.internet.exampleEmail();
    });

    after(() => {
        emailsUsed.forEach(email => {
            identityHelper.deleteAtoUser(email);
        });
    });

    describe("Create User with or without entering any user detail", () => {
        beforeEach("Reload page and setup the routes for roles", () => {
            cy.reload();
            pfeRoutes.setupRouteForGetRoles();
        });

        it("should navigate to admin page when cancel button is clicked", () => {
            createUserPage.cancelButton().should("not.be.disabled").click();
            cy.url().should("include", adminPage.path);
        });

        it("should not be able to save if no data is entered in", () => {
            createUserPage.saveUserButton().should("be.disabled");
        });

        it("should not be able to save when FirstName is not entered ", () => {
            createUserPage.getLastNameField().type(randomLastName);
            createUserPage.getEmailField().type(randomEmail);
            pfeRoutes.verifyGetRoles();
            createUserPage.getAdminFilter().then($filter => {
                cy.wrap($filter).click();
            });
            createUserPage.saveUserButton().should("be.disabled");
        });

        it("should not be able to save when LastName is not entered ", () => {
            createUserPage.getFirstNameField().type(randomFirstName);
            createUserPage.getEmailField().type(randomEmail);
            pfeRoutes.verifyGetRoles();
            createUserPage.getAdminFilter().click().then(() => {
                createUserPage.saveUserButton().should("be.disabled");
            });
        });

        it("should not be able to save when Role is not selected", () => {
            createUserPage.getFirstNameField().type(randomFirstName);
            createUserPage.getLastNameField().type(randomLastName);
            createUserPage.getEmailField().type(randomEmail).then(() => {
                createUserPage.saveUserButton().should("be.disabled");
            });
        });

        it("Data should not be cleared, when user selects stay on Page", () => {
            createUserPage.getFirstNameField().type(randomFirstName);
            createUserPage.getLastNameField().type(randomLastName);
            pfeRoutes.verifyGetRoles();
            createUserPage.getAdminFilter().then($filter => {
                cy.wrap($filter).click();
            });
            createUserPage.getEmailField().type(randomEmail).then(() => {
                createUserPage.cancelButton().click();
            });
            // stay on Page
            unsavedChangesModel.verifyTitle(modalMessage.unsavedChangesTilte);
            unsavedChangesModel.verifyMessage(modalMessage.unsavedChangesMessage);
            unsavedChangesModel.stayOnPageButton().click();

            // Verify the input box contains the data entered earlier
            createUserPage.getFirstNameField().should("have.value", randomFirstName);
            createUserPage.getLastNameField().should("have.value", randomLastName);
            createUserPage.getEmailField().should("have.value", randomEmail);
            createUserPage.saveUserButton().should("not.be.disabled");

            // Navigate back to admin landing page
            clientManagementHelper.cancelAndLeavePage();
        });

        it("should be able to save, when phoneNumber is not entered ", () => {
            createUserPage.getFirstNameField().type(randomFirstName);
            createUserPage.getLastNameField().type(randomLastName);
            createUserPage.getEmailField().type(randomEmail);
            emailsUsed.push(randomEmail);
            pfeRoutes.verifyGetRoles();
            createUserPage.getAdminFilter().click().then(() => {
                clientManagementHelper.saveUser();
            });
        });

        it("Should be able to create User with all fields entered", () => {
            createUserPage.getFirstNameField().type(randomFirstName);
            createUserPage.getLastNameField().type(randomLastName);
            createUserPage.getEmailField().type(randomEmail);
            emailsUsed.push(randomEmail);
            createUserPage.getPhoneNumberField().type(randomPhoneNumber);
            pfeRoutes.verifyGetRoles();
            createUserPage.getAdminFilter().click().then(() => {
                clientManagementHelper.saveUser();
            });
        });
    });

    describe("Verify the Field validation ", () => {
        beforeEach("Reload page and setup the routes for roles", () => {
            cy.reload();
            pfeRoutes.setupRouteForGetRoles();
        });

        it("Should be able save with max length FirstName, lastName, and Email ", () => {
            createUserPage.getFirstNameField().type(maxLengthFirstName);
            createUserPage.getLastNameField().type(maxLengthLastName);
            createUserPage.getEmailField().type(maxLengthEmail);
            emailsUsed.push(maxLengthEmail);
            createUserPage.getPhoneNumberField().type(randomPhoneNumber);
            pfeRoutes.verifyGetRoles();
            createUserPage.getAdminFilter().click().then(() => {
                clientManagementHelper.saveUser();
            });
        });

        it("should provide Error message when Special characters used in FirstName", () => {
            createUserPage.getFirstNameField().type("@//#").then(() => {
                createUserPage.saveUserButton().should("be.disabled");
                createUserPage.getInvalidFieldErrorMessage()
                    .should("have.text", clientMessage.invalidFirstNameMessage);
            });
            createUserPage.cancelButton().should("be.enabled").click();
        });

        it("should provide Error message when Special characters used in LastName", () => {
            createUserPage.getLastNameField().type("$%").then(() => {
                createUserPage.saveUserButton().should("be.disabled");
                createUserPage.getInvalidFieldErrorMessage()
                    .should("have.text", clientMessage.invalidLastNameMessage);
            });
            createUserPage.cancelButton().should("be.enabled").click();
        });

        it("should allow only valid Email Address", () => {
            createUserPage.getEmailField().type("testEmail").then(() => {
                createUserPage.getPhoneNumberField().click();
                createUserPage.getInvalidFieldErrorMessage()
                    .should("have.text", clientMessage.invalidEmailMessage);
            });
        });

        it("should not allow more than 15 Digits in Phone Number Field", () => {
            createUserPage.getPhoneNumberField().type(invalidPhoneNumber).then(() => {
                createUserPage.getInvalidFieldErrorMessage()
                    .should("have.text", clientMessage.invalidPhoneNumberMessage);
            });
        });
    });
});
