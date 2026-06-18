*** Settings ***
Resource    ../../resources/common_keywords.resource

*** Variables ***
${HOME_BUTTON}    xpath=//ion-fab-button[.//ion-icon[@aria-label='home'] or normalize-space(.)='home']
${ARROW_BACK_BUTTON}    xpath=//ion-fab-button[.//ion-icon[@aria-label='arrow back'] or normalize-space(.)='arrow back']
${PASSWORD}    id=password
${PASSWORD_TEXTBOX}    xpath=//input[@placeholder='Password']
${SIGN_IN_BUTTON}    xpath=//ion-button[normalize-space(.)='SIGN IN']
${CLOSE_BUTTON}    xpath=//button[normalize-space(.)='close']

*** Keywords ***
Click Home Button
    Click When Ready    ${HOME_BUTTON}

Click Arrow Back Button
    Click When Ready    ${ARROW_BACK_BUTTON}

Enter Password
    [Arguments]    ${password}
    Wait For Element To Be Ready    ${PASSWORD}
    Input Password    ${PASSWORD}    ${password}

Enter Password Textbox
    [Arguments]    ${password}
    Input Text When Ready    ${PASSWORD_TEXTBOX}    ${password}

Click Sign In Button
    Click When Ready    ${SIGN_IN_BUTTON}

Click Close Button
    Click When Ready    ${CLOSE_BUTTON}

Verify Login Rejected
    Wait For Element To Be Ready    ${SIGN_IN_BUTTON}
    Element Should Be Visible    ${SIGN_IN_BUTTON}

Verify Login Rejected For Blank Credentials
    Wait For Element To Be Ready    ${PASSWORD}
    Element Should Be Visible    ${PASSWORD}
