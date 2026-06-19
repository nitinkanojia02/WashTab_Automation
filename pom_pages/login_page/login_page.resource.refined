*** Settings ***
Resource    ../../resources/common_keywords.resource

*** Variables ***
${USERNAME_FIELD}    xpath=//input[@aria-labelledby='ion-input-0-lbl']
${PASSWORD_FIELD}    id=password
${SIGN_IN_BUTTON}    xpath=//ion-button[.//text()[contains(.,'SIGN IN')] or @text='Login']
${BACK_BUTTON}    xpath=(//ion-fab-button)[1]
${HOME_BUTTON}    xpath=(//ion-fab-button)[last()]

*** Keywords ***
Verify Login Page Loaded
    [Documentation]    Verifies that login page controls are visible and ready for interaction.
    Wait For Element To Be Ready    ${USERNAME_FIELD}
    Wait For Element To Be Ready    ${PASSWORD_FIELD}
    Wait For Element To Be Ready    ${SIGN_IN_BUTTON}
    Wait For Element To Be Ready    ${BACK_BUTTON}
    Wait For Element To Be Ready    ${HOME_BUTTON}

Enter Username
    [Documentation]    Enter text into the User Name field.
    [Arguments]    ${username}
    Input Text When Ready    ${USERNAME_FIELD}    ${username}

Enter Password
    [Documentation]    Enter password into the Password field.
    [Arguments]    ${password}
    Input Text When Ready    ${PASSWORD_FIELD}    ${password}

Submit Login
    [Documentation]    Submits the login form by clicking the Sign In button.
    Click When Ready    ${SIGN_IN_BUTTON}

Login With Credentials
    [Documentation]    Performs login using the provided username and password.
    [Arguments]    ${username}    ${password}
    Enter Username    ${username}
    Enter Password    ${password}
    Submit Login

Click Home Button
    [Documentation]    Click the Home button which navigates to the home page.
    Click When Ready    ${HOME_BUTTON}

Click Back Button
    [Documentation]    Click the Arrow Back button which navigates to the home page.
    Click When Ready    ${BACK_BUTTON}

Verify Login Rejected
    [Documentation]    Verifies login attempt failed and user remains on the login page.
    Wait For Element To Be Ready    ${USERNAME_FIELD}
    Wait For Element To Be Ready    ${PASSWORD_FIELD}
    Location Should Contain    /login

Verify Successful Login Redirect
    [Documentation]    Verifies user is redirected to the home page after successful authentication.
    Location Should Contain    /home