*** Settings ***
Resource    ../../resources/common_keywords.resource

*** Variables ***
${LOGIN_PAGE_URL}    http://172.21.166.115/washtabui/login?data=undefined
${HOME_PAGE_URL}     http://172.21.166.115/washtabui/home
${VALID_USERNAME}    haklarr
${VALID_PASSWORD}    Icstunnel1
${INVALID_USERNAME}  invaliduser
${INVALID_PASSWORD}  wrongpassword
${USERNAME_FIELD}    xpath=//input[@aria-labelledby='ion-input-0-lbl']
${PASSWORD_FIELD}    id=password
${SIGN_IN_BUTTON}    xpath=//ion-button[normalize-space(.)='SIGN IN']
${HOME_NAVIGATION_BUTTON}    xpath=(//ion-fab-button)[last()]
${BACK_NAVIGATION_BUTTON}    xpath=(//ion-fab-button)[1]

*** Keywords ***
Open Login Page
    [Documentation]    Opens the login page using the configured login page URL.
    Open Browser To Url    ${LOGIN_PAGE_URL}

Verify Login Page Loaded
    [Documentation]    Verifies that the login page and its key controls are visible and ready for interaction.
    Wait For Element To Be Ready    ${USERNAME_FIELD}
    Wait For Element To Be Ready    ${PASSWORD_FIELD}
    Wait For Element To Be Ready    ${SIGN_IN_BUTTON}
    Verify Login Navigation Controls Visible

Verify Login Navigation Controls Visible
    [Documentation]    Verifies that Home and Back navigation controls are visible on the login page.
    Wait For Element To Be Ready    ${HOME_NAVIGATION_BUTTON}
    Wait For Element To Be Ready    ${BACK_NAVIGATION_BUTTON}

Enter Username
    [Documentation]    Enter the provided username into the User Name field.
    [Arguments]    ${username}
    Input Text When Ready    ${USERNAME_FIELD}    ${username}

Enter Password
    [Documentation]    Enter the provided password into the Password field.
    [Arguments]    ${password}
    Input Text When Ready    ${PASSWORD_FIELD}    ${password}

Submit Login Form
    [Documentation]    Submits the login form using the Sign In button.
    Click When Ready    ${SIGN_IN_BUTTON}

Click Home Navigation
    [Documentation]    Navigate to the home page using the Home navigation control.
    Click When Ready    ${HOME_NAVIGATION_BUTTON}

Click Back Navigation
    [Documentation]    Navigate using the Back navigation control.
    Click When Ready    ${BACK_NAVIGATION_BUTTON}

Attempt Login With Credentials
    [Documentation]    Attempt authentication using the provided username and password.
    [Arguments]    ${username}    ${password}
    Enter Username    ${username}
    Enter Password    ${password}
    Submit Login Form

Login With Credentials
    [Documentation]    Perform login after verifying the login page is ready.
    [Arguments]    ${username}    ${password}
    Verify Login Page Loaded
    Attempt Login With Credentials    ${username}    ${password}

Login With Valid Credentials
    [Documentation]    Login using the configured valid credentials for the application.
    Verify Login Page Loaded
    Attempt Login With Credentials    ${VALID_USERNAME}    ${VALID_PASSWORD}

Verify Still On Login Page
    [Documentation]    Verifies that the login page remains active by checking the presence of login form controls.
    Wait For Element To Be Ready    ${USERNAME_FIELD}
    Wait For Element To Be Ready    ${SIGN_IN_BUTTON}

Verify Login Failed
    [Documentation]    Verifies that authentication failed by confirming the login page is still displayed.
    Verify Still On Login Page

Verify Login Form Visible
    [Documentation]    Verifies that the login form fields and Sign In button are visible.
    Wait For Element To Be Ready    ${USERNAME_FIELD}
    Wait For Element To Be Ready    ${PASSWORD_FIELD}
    Wait For Element To Be Ready    ${SIGN_IN_BUTTON}
